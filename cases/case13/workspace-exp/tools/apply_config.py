from __future__ import annotations
"""Apply a JSON key-value update to a target config file.

Usage:
    python tools/apply_config.py <target_file> <key> <value>
    python tools/apply_config.py config/app.json worker_threads 8

The value is parsed as JSON (so booleans: true/false, numbers, strings all work).
"""
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: apply_config.py <target_file> <key> <value>")
        return 1

    workspace_dir = Path(__file__).resolve().parent.parent
    target = workspace_dir / sys.argv[1]
    key = sys.argv[2]
    raw_value = sys.argv[3]

    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        value = raw_value  # treat as plain string

    current: dict = {}
    if target.exists():
        current = json.loads(target.read_text(encoding='utf-8'))

    current[key] = value
    target.write_text(json.dumps(current, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({"updated": str(target.relative_to(workspace_dir)), "key": key, "value": value}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
