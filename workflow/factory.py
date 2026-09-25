"""LangGraph factory for one 5GNF. Each stage writes a file, then the run pauses."""

import os
import socket
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from workflow.llm import complete, last_call, pack

LLM_STAGES = {"select", "analyst", "developer", "tester"}

NEXT = {
    "outline": "select",
    "select": "export",
    "export": "analyst",
    "analyst": "developer",
    "developer": "tester",
    "tester": "gate",
    "gate": END,
}


class State(TypedDict, total=False):
    nf: str
    docx: str
    stage: str
    artifact: str
    action: str
    goto: str
    log: str


def arts(nf: str) -> dict[str, Path]:
    # Same filenames for every NF. {nf} is the only prefix.
    return {
        "outline": Path(f"extracts/{nf}-outline.md"),
        "keep": Path(f"extracts/{nf}-keep.txt"),
        "slice": Path(f"extracts/{nf}-slice.md"),
        "scope": Path(f"extracts/{nf}-scope-clarifications.md"),
        "openapi": Path(f"extracts/{nf}-openapi-extract.yaml"),
        "spec": Path(f"specs/{nf}-spec.md"),
        "go": Path(f"{nf}/{nf}.go"),
        "hurl": Path(f"{nf}/test-{nf}.hurl"),
    }


def langfuse_host() -> str:
    # The SDK reads LANGFUSE_HOST. LANGFUSE_BASE_URL is the same web endpoint.
    return os.environ.get("LANGFUSE_HOST", "") or os.environ.get("LANGFUSE_BASE_URL", "")


def tracing_on() -> bool:
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY")
        and os.environ.get("LANGFUSE_SECRET_KEY")
        and langfuse_host()
    )


def traced(name, fn):
    def node(state):
        if not tracing_on():
            return fn(state)
        from langfuse import get_client

        kind = "generation" if name in LLM_STAGES else "span"
        last_call.clear()
        os.environ["LANGFUSE_HOST"] = langfuse_host()
        client = get_client()
        with client.start_as_current_observation(as_type=kind, name=name) as obs:
            # One Langfuse session per NF thread, including a later resume.
            client.update_current_trace(session_id=state["nf"])
            out = fn(state)
            fields = {
                "output": out.get("artifact", ""),
                "metadata": {
                    "finish_reason": last_call.get("finish_reason"),
                    "log": out.get("log", ""),
                    "artifact": out.get("artifact", ""),
                },
            }
            if name in LLM_STAGES:
                usage = last_call.get("usage") or {}
                fields["input"] = {
                    "system": last_call.get("system", ""),
                    "user": last_call.get("user", ""),
                }
                fields["model"] = last_call.get("model")
                fields["usage_details"] = {
                    "input": int(usage.get("prompt_tokens") or 0),
                    "output": int(usage.get("completion_tokens") or 0),
                    "total": int(usage.get("total_tokens") or 0),
                }
            obs.update(**fields)
        # The CLI then waits for a human. Flush now or the batch stays in memory.
        client.flush()
        return out

    return node


def outline(state):
    a = arts(state["nf"])
    subprocess.check_call(
        ["python3", "scripts/extract_docx.py", state["docx"], "--outline", "--out", str(a["outline"])]
    )
    return {"stage": "outline", "artifact": str(a["outline"])}


def select(state):
    a = arts(state["nf"])
    text = complete(
        Path("prompts/select.md").read_text(encoding="utf-8"),
        pack([a["scope"], a["outline"]]),
    )
    a["keep"].write_text(text.strip() + "\n", encoding="utf-8")
    return {"stage": "select", "artifact": str(a["keep"])}


def export(state):
    a = arts(state["nf"])
    keep = a["keep"].read_text(encoding="utf-8").strip()
    subprocess.check_call(
        ["python3", "scripts/extract_docx.py", state["docx"], "--keep", keep, "--out", str(a["slice"])]
    )
    return {"stage": "export", "artifact": str(a["slice"])}


def analyst(state):
    a = arts(state["nf"])
    text = complete(
        Path("prompts/analyst.md").read_text(encoding="utf-8"),
        pack([a["slice"], a["scope"], a["openapi"]]),
    )
    a["spec"].write_text(text, encoding="utf-8")
    return {"stage": "analyst", "artifact": str(a["spec"])}


def developer(state):
    a = arts(state["nf"])
    text = complete(
        Path("prompts/developer.md").read_text(encoding="utf-8"),
        pack([a["spec"], a["openapi"]]),
    )
    a["go"].parent.mkdir(parents=True, exist_ok=True)
    a["go"].write_text(text, encoding="utf-8")
    return {"stage": "developer", "artifact": str(a["go"])}


def tester(state):
    a = arts(state["nf"])
    text = complete(
        Path("prompts/tester.md").read_text(encoding="utf-8"),
        pack([a["spec"], a["scope"], a["openapi"]]),
    )
    a["hurl"].write_text(text, encoding="utf-8")
    return {"stage": "tester", "artifact": str(a["hurl"])}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_until_up(port: int) -> None:
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)


def gate(state):
    # New process each gate, so a previous run's stored profiles are gone.
    a = arts(state["nf"])
    nf = state["nf"]
    log_path = Path(nf) / "test-log.txt"
    lines: list[str] = []
    proc = None
    try:
        built = subprocess.run(
            ["go", "build", "-o", nf, "."],
            cwd=nf,
            capture_output=True,
            text=True,
        )
        lines.append(built.stdout)
        lines.append(built.stderr)
        if built.returncode == 0:
            port = free_port()
            binary = str((Path(nf) / nf).resolve())
            proc = subprocess.Popen([binary], cwd=nf, env={**os.environ, "PORT": str(port)})
            wait_until_up(port)
            tested = subprocess.run(
                ["hurl", "--test", "--variable", f"BASE=http://127.0.0.1:{port}", str(a["hurl"].resolve())],
                capture_output=True,
                text=True,
            )
            lines.append(tested.stdout)
            lines.append(tested.stderr)
    except (OSError, subprocess.SubprocessError) as exc:
        lines.append(f"{exc}\n")
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    log_path.write_text("".join(lines), encoding="utf-8")
    return {"stage": "gate", "artifact": str(a["hurl"]), "log": log_path.read_text(encoding="utf-8")}


def review(state):
    # Pauses the thread. The human edits the artifact file, then resumes.
    decision = interrupt(
        {
            "stage": state["stage"],
            "artifact": state.get("artifact", ""),
            "log": state.get("log", ""),
        }
    )
    return {"action": decision["action"], "goto": decision.get("stage", "")}


def route(state):
    # approve moves on, rerun repeats this stage, goto jumps backward.
    if state.get("action") == "rerun":
        return state["stage"]
    if state.get("action") == "goto":
        return state["goto"]
    return NEXT[state["stage"]]


def build():
    graph = StateGraph(State)
    nodes = {
        "outline": outline,
        "select": select,
        "export": export,
        "analyst": analyst,
        "developer": developer,
        "tester": tester,
        "gate": gate,
    }
    for name, fn in nodes.items():
        graph.add_node(name, traced(name, fn))
    graph.add_node("review", review)
    graph.add_edge(START, "outline")
    for name in NEXT:
        graph.add_edge(name, "review")
    # Every stage name is a legal resume target. END closes the thread.
    path_map = {name: name for name in NEXT}
    path_map[END] = END
    graph.add_conditional_edges("review", route, path_map)
    Path(".workflow").mkdir(exist_ok=True)
    # The connection stays open for the life of this process.
    conn = sqlite3.connect(".workflow/checkpoints.sqlite", check_same_thread=False)
    return graph.compile(checkpointer=SqliteSaver(conn))
