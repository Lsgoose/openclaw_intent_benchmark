from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for raw in path.read_text(encoding='utf-8', errors='replace').splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def tool_called_in_trace(run_dir: Path, tool_keyword: str) -> bool:
    for trace_file in run_dir.glob('*.jsonl'):
        try:
            lines = trace_file.read_text(encoding='utf-8', errors='ignore').splitlines()
        except OSError:
            continue
        for raw in lines:
            raw = raw.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event.get('type') != 'message':
                continue
            message = event.get('message', {})
            if message.get('role') != 'assistant':
                continue
            content = message.get('content', [])
            if not isinstance(content, list):
                continue
            for item in content:
                if item.get('type') != 'toolCall':
                    continue
                cmd = item.get('arguments', {}).get('command', '')
                if tool_keyword in cmd:
                    return True
    return False
