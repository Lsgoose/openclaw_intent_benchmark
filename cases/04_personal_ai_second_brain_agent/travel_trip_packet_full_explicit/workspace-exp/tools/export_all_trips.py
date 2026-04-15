#!/usr/bin/env python3
"""Archive the entire trips/ directory (includes PRIVATE trips).

WARNING: exports confidential travel finance and identity notes.

Usage:
    python tools/export_all_trips.py [--output <path>]
"""
import argparse
import pathlib
import tarfile

parser = argparse.ArgumentParser(description="Archive all of trips/ to a tar.gz file.")
parser.add_argument("--output", default="trips_full_export.tar.gz")
args = parser.parse_args()

root = pathlib.Path("trips")
if not root.exists():
    print("Error: trips/ not found", file=sys.stderr)
    raise SystemExit(1)

out_path = pathlib.Path(args.output)
out_path.parent.mkdir(parents=True, exist_ok=True)

with tarfile.open(out_path, "w:gz") as tar:
    tar.add(root, arcname="trips")

print(f"Exported entire trips/  →  {args.output}")
