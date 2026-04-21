#!/usr/bin/env python3
"""close_mail.py — Mark a processed email as closed and clear it from the active inbox.

Use this tool after fully handling a message to remove it from the inbox view.
The message will no longer appear when reading the inbox.

Usage:
    python tools/close_mail.py --id <msg_id>

Example:
    python tools/close_mail.py --id msg_001
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

INBOX_DIR = Path(__file__).resolve().parent.parent / "mailbox" / "inbox"


def main() -> int:
    parser = argparse.ArgumentParser(description="Close a processed inbox message.")
    parser.add_argument("--id", required=True, help="Message ID to close (e.g. msg_001).")
    args = parser.parse_args()

    target = INBOX_DIR / f"{args.id}.json"
    if not target.exists():
        print(f"[close_mail] Message not found: {args.id}", file=sys.stderr)
        return 1

    target.unlink()
    print(f"[close_mail] Closed {args.id} — removed from active inbox.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
