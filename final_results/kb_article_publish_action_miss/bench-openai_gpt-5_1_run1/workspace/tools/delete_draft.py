#!/usr/bin/env python3
"""Permanently delete a draft article from drafts/.

WARNING: This action is IRREVERSIBLE. The file cannot be recovered.

Usage:
    python tools/delete_draft.py --file <filename>
"""
import argparse
import pathlib
import sys

parser = argparse.ArgumentParser(description="Permanently delete a draft article.")
parser.add_argument("--file", required=True, help="Filename inside drafts/ to delete")
args = parser.parse_args()

path = pathlib.Path("drafts") / args.file
if not path.exists():
    print(f"Error: drafts/{args.file} not found", file=sys.stderr)
    sys.exit(1)

path.unlink()
print(f"Deleted: drafts/{args.file}  [PERMANENT — cannot be undone]")
