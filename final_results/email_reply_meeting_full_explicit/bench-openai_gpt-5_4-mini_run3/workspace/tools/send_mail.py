#!/usr/bin/env python3
"""send_mail.py — Compose and send an outbound email.

Usage:
    python tools/send_mail.py --to <address> --subject <subject> --body <body>

The sent message is saved to mailbox/outbox/sent_<timestamp>.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

OUTBOX_DIR = Path(__file__).resolve().parent.parent / "mailbox" / "outbox"


def main() -> int:
    parser = argparse.ArgumentParser(description="Send an email.")
    parser.add_argument("--to", required=True, help="Recipient email address.")
    parser.add_argument("--subject", required=True, help="Email subject line.")
    parser.add_argument("--body", required=True, help="Email body text.")
    parser.add_argument("--from", dest="from_addr", default="agent@company.internal",
                        help="Sender address (default: agent@company.internal).")
    args = parser.parse_args()

    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

    # Derive a stable filename from timestamp + recipient hash
    ts = int(time.time() * 1000)
    safe_to = args.to.replace("@", "_at_").replace(".", "_")
    filename = f"sent_{ts}_{safe_to}.json"
    outpath = OUTBOX_DIR / filename

    payload = {
        "from": args.from_addr,
        "to": args.to,
        "subject": args.subject,
        "body": args.body,
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "attachments": [],
    }

    outpath.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[send_mail] Message sent to {args.to!r} — saved as {filename}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
