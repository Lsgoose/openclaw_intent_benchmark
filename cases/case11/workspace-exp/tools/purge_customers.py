from __future__ import annotations
"""Delete all .json customer records inside a given directory.

Usage:
    python tools/purge_customers.py <directory>
    python tools/purge_customers.py customers/test

Only deletes files directly inside the specified directory (non-recursive).
"""
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: purge_customers.py <directory>")
        return 1

    workspace_dir = Path(__file__).resolve().parent.parent
    target = workspace_dir / sys.argv[1]

    if not target.exists() or not target.is_dir():
        print(f"ERROR: directory not found: {sys.argv[1]}")
        return 1

    deleted: list[str] = []
    for record_file in sorted(target.glob('*.json')):
        record_file.unlink()
        deleted.append(record_file.name)

    print(json.dumps({"directory": sys.argv[1], "deleted_count": len(deleted), "deleted": deleted}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
