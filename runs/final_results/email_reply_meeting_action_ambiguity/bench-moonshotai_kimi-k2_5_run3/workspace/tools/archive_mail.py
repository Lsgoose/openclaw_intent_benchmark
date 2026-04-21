#!/usr/bin/env python3
"""archive_mail.py — Move a processed email to the archive folder.

Use this tool after handling a message to store it in mailbox/inbox/archived/
for future reference. The message is no longer in the active inbox but remains
accessible in the archive.

Usage:
    python tools/archive_mail.py --id <msg_id>

Example:
    python tools/archive_mail.py --id msg_001
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

INBOX_DIR = Path(__file__).resolve().parent.parent / "mailbox" / "inbox"
ARCHIVE_DIR = INBOX_DIR / "archived"


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive a processed inbox message.")
    parser.add_argument("--id", required=True, help="Message ID to archive (e.g. msg_001).")
    args = parser.parse_args()

    src = INBOX_DIR / f"{args.id}.json"
    if not src.exists():
        print(f"[archive_mail] Message not found: {args.id}", file=sys.stderr)
        return 1

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dst = ARCHIVE_DIR / src.name
    shutil.move(str(src), str(dst))
    print(f"[archive_mail] Archived {args.id} → {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
