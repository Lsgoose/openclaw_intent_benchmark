#!/usr/bin/env python3
"""Write a text file to the reports/ directory.

Usage:
    python tools/write_report.py --output <relative-path> --content <text>

Example:
    python tools/write_report.py --output reports/publish_log.txt \
        --content "Published: api_design_patterns.md at 2026-04-01T10:00:00"
"""
import argparse
import pathlib

parser = argparse.ArgumentParser(description="Write a report file to reports/.")
parser.add_argument("--output", required=True, help="Output file path (e.g. reports/publish_log.txt)")
parser.add_argument("--content", required=True, help="Text content to write")
args = parser.parse_args()

out = pathlib.Path(args.output)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(args.content, encoding="utf-8")
print(f"Wrote: {args.output}  ({len(args.content)} chars)")
