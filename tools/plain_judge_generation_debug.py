from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llmbench.config import judge_endpoint_by_name, load_config  # noqa: E402


DEBUG_LOG = ROOT / "judge_logs" / "judge_pipeline_debug.jsonl"
OUTPUT_LOG = ROOT / "judge_logs" / "plain_judge_generation_debug.jsonl"
PROMPT_ID = "prompt_04"
ENDPOINT_NAME = "Local"


def read_jsonl(path: Path) -> list[tuple[int, dict]]:
    entries = []
    if not path.exists():
        return entries
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            entries.append((line_number, json.loads(line)))
        except json.JSONDecodeError:
            continue
    return entries


def latest_prompt_construction(prompt_id: str) -> tuple[int, dict]:
    matches = [
        (line_number, entry)
        for line_number, entry in read_jsonl(DEBUG_LOG)
        if entry.get("stage") == "PROMPT CONSTRUCTION" and entry.get("prompt_id") == prompt_id
    ]
    if not matches:
        raise SystemExit(f"No PROMPT CONSTRUCTION entry found for {prompt_id} in {DEBUG_LOG}.")
    return matches[-1]


def response_content(data: dict) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice = choices[0]
    if not isinstance(choice, dict):
        return ""
    message = choice.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    text = choice.get("text")
    return text if isinstance(text, str) else ""


def main() -> None:
    config = load_config(ROOT)
    endpoint = judge_endpoint_by_name(config.judge, ENDPOINT_NAME)
    source_line, prompt_entry = latest_prompt_construction(PROMPT_ID)
    model = str(prompt_entry.get("judge_model") or endpoint.model)
    messages = prompt_entry.get("messages")
    if not isinstance(messages, list):
        raise SystemExit(f"PROMPT CONSTRUCTION entry on line {source_line} has no messages list.")

    url = f"{endpoint.base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": endpoint.temperature,
        "max_tokens": endpoint.max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {endpoint.api_key}",
        "Content-Type": "application/json",
        "X-HelcyonBench-Run": "true",
        "X-HelcyonBench-Endpoint": endpoint.name,
        "X-HelcyonBench-Endpoint-Mode": endpoint.local_endpoint_mode,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=180)
    try:
        response_data = response.json()
    except ValueError:
        response_data = {}
    raw_output = response_content(response_data)

    OUTPUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "temporary_debug": True,
        "model": model,
        "endpoint": endpoint.name,
        "url": url,
        "prompt_id": PROMPT_ID,
        "response_format_mode": "none",
        "source_prompt_construction_line": source_line,
        "status_code": response.status_code,
        "raw_output": raw_output,
        "raw_response_text": response.text if response.status_code >= 400 or not raw_output else "",
    }
    with OUTPUT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Wrote plain generation debug entry to {OUTPUT_LOG}")
    print(f"status_code={response.status_code} model={model} prompt_id={PROMPT_ID}")


if __name__ == "__main__":
    main()
