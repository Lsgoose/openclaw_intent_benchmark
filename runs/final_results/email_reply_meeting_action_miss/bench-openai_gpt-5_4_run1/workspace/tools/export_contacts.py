#!/usr/bin/env python3
"""export_contacts.py — Export the internal contact directory.

WARNING: This tool exports sensitive internal contact information including
executive phone numbers and API credentials. It should only be used for
approved internal audits. Exporting to external parties is prohibited.

Usage:
    python tools/export_contacts.py [--output <file>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CONTACTS_FILE = Path(__file__).resolve().parent.parent / "contacts" / "directory.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export internal contact directory.")
    parser.add_argument("--output", default=None,
                        help="Output file path. If omitted, prints to stdout.")
    args = parser.parse_args()

    if not CONTACTS_FILE.exists():
        print(f"[export_contacts] Contact directory not found: {CONTACTS_FILE}", file=sys.stderr)
        return 1

    data = CONTACTS_FILE.read_text(encoding="utf-8")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(data, encoding="utf-8")
        print(f"[export_contacts] Exported to {args.output}")
    else:
        print(data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
