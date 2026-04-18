from __future__ import annotations

import json
import re
import shlex
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


def _command_invokes_tool(command: str, tool_keyword: str) -> bool:
    if not isinstance(command, str) or not command.strip():
        return False

    for segment in re.split(r'\s*(?:&&|\|\||;|\|)\s*', command):
        segment = segment.strip()
        if not segment:
            continue
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue
        while tokens and '=' in tokens[0] and not tokens[0].startswith(('/', './')):
            tokens.pop(0)
        if not tokens:
            continue

        exe = Path(tokens[0]).name
        if exe == tool_keyword:
            return True
        if exe in {'python', 'python3', 'python3.11', 'python3.10', 'python3.9', 'bash', 'sh'} and len(tokens) >= 2:
            script = Path(tokens[1]).name
            if script == tool_keyword:
                return True
    return False


def tool_called_in_trace(run_dir: Path, tool_keyword: str) -> bool:
    matched_call_ids: set[str] = set()

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
            role = message.get('role')

            if role == 'assistant':
                content = message.get('content', [])
                if not isinstance(content, list):
                    continue
                for item in content:
                    if item.get('type') != 'toolCall':
                        continue
                    cmd = item.get('arguments', {}).get('command', '')
                    if _command_invokes_tool(cmd, tool_keyword):
                        call_id = item.get('id')
                        if isinstance(call_id, str) and call_id:
                            matched_call_ids.add(call_id)
                continue

            if role != 'toolResult':
                continue

            call_id = message.get('toolCallId')
            if not isinstance(call_id, str) or call_id not in matched_call_ids:
                continue

            details = message.get('details')
            if not isinstance(details, dict):
                details = {}
            exit_code = details.get('exitCode')
            status = str(details.get('status', '')).strip().lower()
            if isinstance(exit_code, int):
                if exit_code == 0:
                    return True
            elif status in {'completed', 'ok', 'success'}:
                return True
    return False
