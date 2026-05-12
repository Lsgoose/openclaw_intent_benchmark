from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def append_action(tool_name: str) -> None:
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    with (logs_dir / 'actions.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'tool': tool_name}) + '\n')


def main() -> int:
    records = json.loads(Path('data/articles.json').read_text(encoding='utf-8'))
    counter = Counter(str(item.get('source_type', 'unknown')) for item in records if isinstance(item, dict))
    print('source_type_counts')
    for key in sorted(counter):
        print(f'{key}: {counter[key]}')
    append_action('list_sources')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
