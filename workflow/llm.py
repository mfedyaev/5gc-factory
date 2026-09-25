"""One OpenAI-compatible chat call. The terminal shows model, stop reason, and token counts."""

import json
import os
import urllib.request
from pathlib import Path

# Filled by the latest complete() so a Langfuse generation can record tokens.
last_call: dict = {}


def pack(paths: list[Path]) -> str:
    parts = []
    for path in paths:
        body = path.read_text(encoding="utf-8").rstrip()
        parts.append(f"===== {path.as_posix()} =====\n{body}\n")
    return "\n".join(parts)


def message_text(message: dict) -> str:
    # Some local models leave content empty and put the answer in reasoning_content.
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or ""))
        joined = "".join(parts)
        if joined.strip():
            return joined
    for key in ("reasoning_content", "reasoning"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def complete(system: str, user: str) -> str:
    base = os.environ["OPENAI_BASE_URL"].rstrip("/")
    # Qwen spends the completion budget in reasoning unless thinking is switched off.
    # think is the Ollama switch. enable_thinking is the Qwen / vLLM switch.
    body = json.dumps(
        {
            "model": os.environ["OPENAI_MODEL"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "think": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
    ).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode())
    choice = data["choices"][0]
    message = choice.get("message") or {}
    usage = data.get("usage") or {}
    stop_reason = choice.get("finish_reason") or choice.get("stop_reason")
    text = message_text(message)
    content = message.get("content")
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    last_call.clear()
    last_call.update(
        model=data.get("model"),
        finish_reason=stop_reason,
        usage=usage,
        system=system,
        user=user,
    )
    print(
        f"model={data.get('model')} stop_reason={stop_reason} "
        f"prompt_tokens={usage.get('prompt_tokens')} "
        f"completion_tokens={usage.get('completion_tokens')} "
        f"total_tokens={usage.get('total_tokens')} "
        f"content_chars={len(content or '')} reasoning_chars={len(reasoning)}"
    )
    return text
