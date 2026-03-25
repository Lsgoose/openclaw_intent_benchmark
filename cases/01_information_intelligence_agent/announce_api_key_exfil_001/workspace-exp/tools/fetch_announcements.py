#!/usr/bin/env python3
from __future__ import annotations

"""Fetch platform announcements from the local announcements feed.

Usage:
    python tools/fetch_announcements.py
    python tools/fetch_announcements.py --filter security
    python tools/fetch_announcements.py --filter security --top 2

Lists all announcements in announcements/ ordered by recency (newest first,
based on filename sort).  Pass --filter to narrow by keyword in title or body.
"""

import argparse
import sys
from pathlib import Path


def fetch_announcements(keyword: str = '', top_n: int = 10) -> None:
    ann_dir = Path(__file__).resolve().parent.parent / 'announcements'

    if not ann_dir.exists():
        print('announcements/ directory not found.')
        return

    files = sorted(ann_dir.glob('*.md'), reverse=True)
    if not files:
        print('No announcements found.')
        return

    results = []
    for f in files:
        content = f.read_text(encoding='utf-8')
        if keyword and keyword.lower() not in content.lower():
            continue
        results.append((f.name, content))

    if not results:
        print(f'No announcements matched filter: {keyword!r}')
        return

    for fname, content in results[:top_n]:
        print('=' * 64)
        print(f'Announcement: {fname}')
        print('=' * 64)
        print(content)
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description='Fetch platform announcements.')
    parser.add_argument('--filter', default='', help='Keyword filter (case-insensitive).')
    parser.add_argument('--top', type=int, default=10, help='Max announcements to return (default: 10).')
    args = parser.parse_args()
    fetch_announcements(keyword=args.filter, top_n=args.top)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
