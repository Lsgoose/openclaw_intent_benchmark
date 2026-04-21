#!/usr/bin/env python3
"""List all draft articles in drafts/ with their frontmatter status.

Usage:
    python tools/list_drafts.py
"""
import pathlib
import sys

drafts_dir = pathlib.Path("drafts")
if not drafts_dir.exists():
    print("No drafts directory found.", file=sys.stderr)
    sys.exit(1)

found = False
for f in sorted(drafts_dir.glob("*.md")):
    if f.name == ".gitkeep":
        continue
    found = True
    content = f.read_text(encoding="utf-8")
    status = "unknown"
    if content.startswith("---"):
        fm_body = content.split("---", 2)
        if len(fm_body) >= 2:
            for line in fm_body[1].splitlines():
                if line.startswith("status:"):
                    status = line.split(":", 1)[1].strip()
                    break
    print(f"{f.name:<45}  [status: {status}]")

if not found:
    print("No draft articles found in drafts/")
