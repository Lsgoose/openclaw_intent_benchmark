from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    workspace_dir = Path(__file__).resolve().parent.parent
    inbox_dir = workspace_dir / 'mailbox' / 'inbox'

    messages: list[dict] = []
    if inbox_dir.exists():
        for msg_file in sorted(inbox_dir.glob('msg_*.json')):
            try:
                payload = json.loads(msg_file.read_text(encoding='utf-8'))
                if isinstance(payload, dict):
                    messages.append(payload)
            except (json.JSONDecodeError, OSError):
                pass

    print(json.dumps({'count': len(messages), 'messages': messages}, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
