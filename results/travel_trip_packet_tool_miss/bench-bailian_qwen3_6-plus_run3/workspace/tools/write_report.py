#!/usr/bin/env python3
"""Write a text file under reports/.

Usage:
    python tools/write_report.py --output <relative-path> --content <text>
"""
import argparse
import pathlib

parser = argparse.ArgumentParser(description="Write a report file under reports/.")
parser.add_argument("--output", required=True)
parser.add_argument("--content", required=True)
args = parser.parse_args()

out = pathlib.Path(args.output)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(args.content, encoding="utf-8")
print(f"Wrote: {args.output}  ({len(args.content)} chars)")
