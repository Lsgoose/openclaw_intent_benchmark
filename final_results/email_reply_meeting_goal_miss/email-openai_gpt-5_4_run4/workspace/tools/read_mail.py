#!/usr/bin/env python3
"""read_mail.py — List and display all inbox messages.

Usage:
    python tools/read_mail.py
    python tools/read_mail.py --id msg_001

Output:
    Prints each message as formatted JSON, separated by a divider line.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

INBOX_DIR = Path(__file__).resolve().parent.parent / "mailbox" / "inbox"


def load_messages(msg_id: str | None = None) -> list[dict]:
    if not INBOX_DIR.exists():
        print(f"[read_mail] Inbox directory not found: {INBOX_DIR}", file=sys.stderr)
        return []

    files = sorted(INBOX_DIR.glob("msg_*.json"))
    messages = []
    for path in files:
        try:
            msg = json.loads(path.read_text(encoding="utf-8"))
            if msg_id is None or msg.get("msg_id") == msg_id:
                messages.append(msg)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[read_mail] Warning: could not read {path.name}: {exc}", file=sys.stderr)

    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Read inbox messages.")
    parser.add_argument("--id", dest="msg_id", default=None, help="Show only a specific message ID.")
    args = parser.parse_args()

    messages = load_messages(args.msg_id)

    if not messages:
        print("[read_mail] No messages found.")
        return 0

    print(f"[read_mail] Found {len(messages)} message(s).\n")
    divider = "-" * 60
    for msg in messages:
        print(divider)
        print(json.dumps(msg, indent=2, ensure_ascii=False))
    print(divider)
    return 0


if __name__ == "__main__":
    sys.exit(main())
