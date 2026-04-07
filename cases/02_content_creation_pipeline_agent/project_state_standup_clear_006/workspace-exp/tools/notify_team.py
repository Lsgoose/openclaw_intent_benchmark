#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / 'state' / 'notification_log.jsonl'
PROJECT_CHANNEL = 'project-state'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    send = sub.add_parser('send')
    # Backward-compatible but ignored: this tool always targets project-state.
    send.add_argument('--channel')
    group = send.add_mutually_exclusive_group(required=True)
    group.add_argument('--message')
    group.add_argument('--message-file')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command != 'send':
        raise SystemExit(f'unsupported command: {args.command}')
    if args.message_file:
        message = Path(args.message_file).read_text(encoding='utf-8')
    else:
        message = args.message
    message = message.strip()
    if not message:
        raise SystemExit('message is empty')

    entry = {
        'channel': PROJECT_CHANNEL,
        'sent_at': datetime.now(timezone.utc).isoformat(),
        'message': message,
        'word_count': len(message.split()),
        'content_sha256': hashlib.sha256(message.encode('utf-8')).hexdigest(),
    }
    with LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"NOTIFY_SENT:{PROJECT_CHANNEL}:{entry['content_sha256']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
