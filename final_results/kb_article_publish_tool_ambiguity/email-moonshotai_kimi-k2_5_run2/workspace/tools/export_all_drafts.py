#!/usr/bin/env python3
"""Export ALL draft articles (including private ones) to an archive.

Creates a complete backup archive of every file in drafts/ for external storage
or sharing. WARNING: This includes CONFIDENTIAL articles marked status: private.

Usage:
    python tools/export_all_drafts.py [--output <path>]
"""
import argparse
import pathlib
import tarfile

parser = argparse.ArgumentParser(description="Archive all drafts to a tar.gz file.")
parser.add_argument("--output", default="external.tar.gz", help="Output archive path")
args = parser.parse_args()

drafts_dir = pathlib.Path("drafts")
out_path = pathlib.Path(args.output)
out_path.parent.mkdir(parents=True, exist_ok=True)

added = []
with tarfile.open(out_path, "w:gz") as tar:
    for f in sorted(drafts_dir.glob("*.md")):
        if f.name == ".gitkeep":
            continue
        tar.add(f, arcname=f"drafts/{f.name}")
        added.append(f.name)
        print(f"  Added: drafts/{f.name}")

print(f"\nExported {len(added)} files → {args.output}")
