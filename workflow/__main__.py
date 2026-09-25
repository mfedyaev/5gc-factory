"""Run or resume one NF thread. The thread id is the NF name."""

import warnings

# This interpreter links LibreSSL. urllib3 v2 warns on import; the chat calls still work.
warnings.filterwarnings("ignore", message=r"urllib3 v2 only supports OpenSSL")

import argparse
import os
import sys
from pathlib import Path

from langgraph.types import Command

from workflow.factory import build


def unquote(value: str) -> str:
    # .env files often store OPENAI_BASE_URL="http://..."
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def load_env() -> None:
    # Optional .env in the repo root. A variable already in the shell wins.
    path = Path(".env")
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), unquote(value))


def ask(payload: dict):
    print(f"\nPaused at {payload.get('stage')}")
    print(f"Artifact: {payload.get('artifact')}")
    log = payload.get("log") or ""
    if log:
        print(log)
    if not sys.stdin.isatty():
        print("Resume: python -m workflow resume --nf <nf> --action approve|rerun|goto --stage <name>")
        return None
    action = input("action [approve|rerun|goto]: ").strip() or "approve"
    stage = input("stage: ").strip() if action == "goto" else ""
    return {"action": action, "stage": stage}


def until_pause(graph, config, first) -> None:
    graph.invoke(first, config)
    while True:
        snap = graph.get_state(config)
        if not snap.interrupts:
            print("Finished.")
            return
        decision = ask(snap.interrupts[0].value)
        if decision is None:
            return
        graph.invoke(Command(resume=decision), config)


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="5GNF factory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run")
    run.add_argument("--nf", required=True)
    run.add_argument("--docx", required=True)

    resume = sub.add_parser("resume")
    resume.add_argument("--nf", required=True)
    resume.add_argument("--action", choices=["approve", "rerun", "goto"], required=True)
    resume.add_argument("--stage", default="")

    args = parser.parse_args()
    graph = build()
    config = {"configurable": {"thread_id": args.nf}}
    if args.cmd == "run":
        first = {"nf": args.nf, "docx": args.docx, "action": "approve"}
    else:
        snap = graph.get_state(config)
        if snap.interrupts:
            first = Command(resume={"action": args.action, "stage": args.stage})
        elif snap.next:
            # Approve already moved the thread, then the stage raised. Run it again.
            print(f"Retrying {snap.next[0]}")
            first = None
        else:
            raise SystemExit("This thread is already finished.")
    until_pause(graph, config, first)


if __name__ == "__main__":
    main()
