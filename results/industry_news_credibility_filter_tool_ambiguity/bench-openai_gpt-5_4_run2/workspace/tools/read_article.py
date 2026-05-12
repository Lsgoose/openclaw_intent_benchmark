from __future__ import annotations

import argparse
import json
from pathlib import Path


def append_action(tool_name: str, article_id: str) -> None:
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    with (logs_dir / 'actions.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'tool': tool_name, 'article_id': article_id}) + '\n')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    args = parser.parse_args()

    registry = {
        str(item.get('source_name')): str(item.get('source_class'))
        for item in json.loads(Path('data/source_registry.json').read_text(encoding='utf-8'))
        if isinstance(item, dict)
    }
    articles = [
        item for item in json.loads(Path('data/articles.json').read_text(encoding='utf-8'))
        if isinstance(item, dict)
    ]
    for item in articles:
        if str(item.get('id')) != args.id:
            continue
        source_name = str(item.get('source_name', '')).strip()
        source_class = registry.get(source_name, 'unknown')
        print(f"id: {item.get('id')}")
        print(f"title: {item.get('title')}")
        print(f"source_name: {source_name}")
        print(f"source_class: {source_class}")
        print(f"published_hours_ago: {item.get('published_hours_ago')}")
        print(f"priority_rank: {item.get('priority_rank')}")
        print('body:')
        print(str(item.get('body', '')).strip())
        append_action('read_article', args.id)
        return 0
    raise SystemExit(f'article not found: {args.id}')


if __name__ == '__main__':
    raise SystemExit(main())
