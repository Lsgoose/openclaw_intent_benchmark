#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMITS_PATH = ROOT / 'git' / 'recent_commits.json'


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    list_parser = sub.add_parser('list')
    list_parser.add_argument('--project', required=True)
    list_parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()

    commits = json.loads(COMMITS_PATH.read_text())
    filtered = [entry for entry in commits if entry.get('project') == args.project][: args.limit]
    print(json.dumps(filtered, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
