#!/usr/bin/env python3
"""Copy a trips/ file into shared_package/ (original preserved).

Usage:
    python tools/copy_to_package.py --trip <trip_id> --file <filename>
"""
import argparse
import pathlib
import shutil
import sys

parser = argparse.ArgumentParser(description="Copy a trip file into shared_package/.")
parser.add_argument("--trip", required=True)
parser.add_argument("--file", required=True)
args = parser.parse_args()

src = pathlib.Path("trips") / args.trip / args.file
if not src.exists():
    print(f"Error: {src} not found", file=sys.stderr)
    sys.exit(1)

dst = pathlib.Path("shared_package") / args.trip / args.file
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, dst)
print(f"Copied: trips/{args.trip}/{args.file}  →  shared_package/{args.trip}/{args.file}")
