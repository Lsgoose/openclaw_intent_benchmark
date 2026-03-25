from __future__ import annotations

"""Search the personal knowledge base for notes matching a query.

Usage:
    python tools/search_kb.py "api integration vendor"
    python tools/search_kb.py "deployment checklist" --top 3

Returns the top matching notes from knowledge_base/ ordered by relevance.
Relevance = sum of per-term occurrence counts across the document.
"""

import argparse
import sys
from pathlib import Path


def score_document(content: str, terms: list[str]) -> int:
    lowered = content.lower()
    return sum(lowered.count(term) for term in terms)


def search_kb(query: str, top_n: int = 3) -> None:
    kb_dir = Path(__file__).resolve().parent.parent / 'knowledge_base'

    if not kb_dir.exists():
        print('knowledge_base/ directory not found.')
        return

    terms = [t.strip().lower() for t in query.split() if t.strip()]
    if not terms:
        print('No query terms provided.')
        return

    results: list[tuple[int, str, str]] = []
    for md_file in sorted(kb_dir.glob('*.md')):
        content = md_file.read_text(encoding='utf-8')
        score = score_document(content, terms)
        if score > 0:
            results.append((score, md_file.name, content))

    if not results:
        print('No matching notes found for query:', query)
        return

    results.sort(key=lambda r: r[0], reverse=True)

    for score, fname, content in results[:top_n]:
        print('=' * 64)
        print(f'Note: {fname}  (relevance: {score})')
        print('=' * 64)
        print(content)
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description='Search the personal knowledge base.')
    parser.add_argument('query', nargs='+', help='Search query words.')
    parser.add_argument('--top', type=int, default=3, help='Number of results to return (default: 3).')
    args = parser.parse_args()
    search_kb(' '.join(args.query), top_n=args.top)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
