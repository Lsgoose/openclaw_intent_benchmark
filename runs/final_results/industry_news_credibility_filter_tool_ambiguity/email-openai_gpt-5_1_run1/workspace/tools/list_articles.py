from __future__ import annotations

import json
from pathlib import Path


def append_action(tool_name: str) -> None:
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    with (logs_dir / 'actions.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'tool': tool_name}) + '\n')


def main() -> int:
    registry = {
        str(item.get('source_name')): str(item.get('source_class'))
        for item in json.loads(Path('data/source_registry.json').read_text(encoding='utf-8'))
        if isinstance(item, dict)
    }
    articles = [
        item for item in json.loads(Path('data/articles.json').read_text(encoding='utf-8'))
        if isinstance(item, dict)
    ]
    articles.sort(key=lambda item: (int(item.get('priority_rank', 9999)), str(item.get('title', '')).lower()))
    for item in articles:
        source_name = str(item.get('source_name', '')).strip()
        source_class = registry.get(source_name, 'unknown')
        print(
            f"{item.get('id')} | priority_rank={item.get('priority_rank')} | published_hours_ago={item.get('published_hours_ago')} | source_class={source_class} | source_name={source_name} | title={item.get('title')}"
        )
    append_action('list_articles')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
