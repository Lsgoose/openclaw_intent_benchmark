#!/usr/bin/env python3
"""List trips and share_status from trips/catalog.json.

Usage:
    python tools/list_trips.py
"""
import json
import pathlib
import sys

catalog_path = pathlib.Path("trips") / "catalog.json"
if not catalog_path.exists():
    print("Error: trips/catalog.json not found", file=sys.stderr)
    sys.exit(1)

data = json.loads(catalog_path.read_text(encoding="utf-8"))
trips = data.get("trips", {})
if not trips:
    print("No trips in catalog.")
    raise SystemExit(0)

for tid in sorted(trips.keys()):
    meta = trips[tid] or {}
    title = meta.get("title", "")
    status = meta.get("share_status", "unknown")
    print(f"{tid:<28}  share_status={status:<10}  {title}")
