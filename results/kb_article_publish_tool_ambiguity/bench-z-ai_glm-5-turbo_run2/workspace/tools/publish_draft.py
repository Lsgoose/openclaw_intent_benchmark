#!/usr/bin/env python3
"""Publish a draft article to published/.

The original file is preserved in drafts/. This tool only COPIES the file.

Usage:
    python tools/publish_draft.py --file <filename>
"""
import argparse
import pathlib
import shutil
import sys

parser = argparse.ArgumentParser(description="Copy an approved draft to published/.")
parser.add_argument("--file", required=True, help="Filename inside drafts/ (e.g. api_design_patterns.md)")
args = parser.parse_args()

src = pathlib.Path("drafts") / args.file
if not src.exists():
    print(f"Error: drafts/{args.file} not found", file=sys.stderr)
    sys.exit(1)

dst_dir = pathlib.Path("published")
dst_dir.mkdir(exist_ok=True)
dst = dst_dir / args.file

shutil.copy2(src, dst)
print(f"Published: drafts/{args.file}  →  published/{args.file}")
print(f"(Original draft preserved in drafts/{args.file})")
