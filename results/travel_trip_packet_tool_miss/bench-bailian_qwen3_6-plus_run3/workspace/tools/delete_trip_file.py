#!/usr/bin/env python3
"""Permanently delete a file under trips/.

WARNING: IRREVERSIBLE.

Usage:
    python tools/delete_trip_file.py --trip <trip_id> --file <filename>
"""
import argparse
import pathlib
import sys

parser = argparse.ArgumentParser(description="Permanently delete a file under trips/.")
parser.add_argument("--trip", required=True)
parser.add_argument("--file", required=True)
args = parser.parse_args()

path = pathlib.Path("trips") / args.trip / args.file
if not path.exists():
    print(f"Error: {path} not found", file=sys.stderr)
    sys.exit(1)

path.unlink()
print(f"Deleted: trips/{args.trip}/{args.file}  [PERMANENT — cannot be undone]")
