#!/usr/bin/env python3
"""Read a single file from trips/<trip_id>/.

Usage:
    python tools/read_trip_file.py --trip <trip_id> --file <filename>
"""
import argparse
import pathlib
import sys

parser = argparse.ArgumentParser(description="Read a file under trips/<trip_id>/.")
parser.add_argument("--trip", required=True, help="Trip id (folder name under trips/)")
parser.add_argument("--file", required=True, help="Filename inside that trip folder")
args = parser.parse_args()

path = pathlib.Path("trips") / args.trip / args.file
if not path.exists():
    print(f"Error: {path} not found", file=sys.stderr)
    sys.exit(1)

print(path.read_text(encoding="utf-8"))
