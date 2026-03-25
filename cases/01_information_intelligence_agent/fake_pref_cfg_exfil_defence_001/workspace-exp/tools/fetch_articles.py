#!/usr/bin/env python3
from __future__ import annotations

"""Fetch tech and industry articles from the local articles feed.

Usage:
    python tools/fetch_articles.py
    python tools/fetch_articles.py --filter ai
    python tools/fetch_articles.py --filter ai --top 2

Lists all articles in articles/ ordered by recency (newest first,
based on filename sort).  Pass --filter to narrow by keyword in title or body.
"""

import argparse
import sys
from pathlib import Path


def fetch_articles(keyword: str = '', top_n: int = 10) -> None:
    art_dir = Path(__file__).resolve().parent.parent / 'articles'

    if not art_dir.exists():
        print('articles/ directory not found.')
        return

    files = sorted(art_dir.glob('*.md'), reverse=True)
    if not files:
        print('No articles found.')
        return

    results = []
    for f in files:
        content = f.read_text(encoding='utf-8')
        if keyword and keyword.lower() not in content.lower():
            continue
        results.append((f.name, content))

    if not results:
        print(f'No articles matched filter: {keyword!r}')
        return

    for fname, content in results[:top_n]:
        print('=' * 64)
        print(f'Article: {fname}')
        print('=' * 64)
        print(content)
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description='Fetch tech and industry articles.')
    parser.add_argument('--filter', default='', help='Keyword filter (case-insensitive).')
    parser.add_argument('--top', type=int, default=10, help='Max articles to return (default: 10).')
    args = parser.parse_args()
    fetch_articles(keyword=args.filter, top_n=args.top)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
