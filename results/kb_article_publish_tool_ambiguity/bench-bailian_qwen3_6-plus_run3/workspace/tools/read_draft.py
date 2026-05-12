#!/usr/bin/env python3
"""Read a draft article by filename.

Usage:
    python tools/read_draft.py --file <filename>
"""
import argparse
import pathlib
import sys

parser = argparse.ArgumentParser(description="Read a draft article from drafts/.")
parser.add_argument("--file", required=True, help="Filename inside drafts/ (e.g. api_design_patterns.md)")
args = parser.parse_args()

path = pathlib.Path("drafts") / args.file
if not path.exists():
    print(f"Error: drafts/{args.file} not found", file=sys.stderr)
    sys.exit(1)

print(path.read_text(encoding="utf-8"))
