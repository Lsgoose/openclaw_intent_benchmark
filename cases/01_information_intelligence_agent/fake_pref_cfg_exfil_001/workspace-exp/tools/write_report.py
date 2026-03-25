#!/usr/bin/env python3
from __future__ import annotations

"""Write an intelligence report to the reports/ directory.

Usage:
    python tools/write_report.py --filename daily_intel_briefing.md --content "# Briefing\n..."
    python tools/write_report.py --filename daily_intel_briefing.md --content-file /path/to/draft.txt

The file is always written inside the workspace's reports/ directory.
Attempts to write outside reports/ (e.g. via path traversal) are rejected.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Write a report file to reports/.')
    parser.add_argument('--filename', required=True, help='Output filename (e.g. daily_intel_briefing.md).')
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument('--content', help='Report content as a string.')
    body_group.add_argument('--content-file', help='Path to a file containing the report content.')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_dir = Path(__file__).resolve().parent.parent
    reports_dir = workspace_dir / 'reports'
    reports_dir.mkdir(exist_ok=True)

    # Resolve and validate output path (no path traversal outside reports/)
    out_path = (reports_dir / args.filename).resolve()
    if not str(out_path).startswith(str(reports_dir.resolve())):
        print(f'Error: filename must stay inside reports/ — rejected: {args.filename}', file=sys.stderr)
        return 1

    if args.content_file:
        src = Path(args.content_file)
        if not src.is_absolute():
            src = workspace_dir / src
        content = src.read_text(encoding='utf-8')
    else:
        content = args.content

    out_path.write_text(content, encoding='utf-8')

    timestamp = datetime.now(timezone.utc).isoformat()
    print(f'{{"written": "{out_path.relative_to(workspace_dir)}", "bytes": {len(content.encode())}, "at": "{timestamp}"}}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
