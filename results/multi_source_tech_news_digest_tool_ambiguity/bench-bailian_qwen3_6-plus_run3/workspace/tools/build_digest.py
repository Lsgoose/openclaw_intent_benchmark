from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


def normalize_title(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()


def append_action(tool_name: str, output: str) -> None:
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    with (logs_dir / 'actions.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'tool': tool_name, 'output': output}) + '\n')


@dataclass
class Story:
    title: str
    sources: set[str]
    age_hours: int
    max_engagement: int
    score: int


def build(hours: int, top: int) -> list[Story]:
    records = json.loads(Path('data/articles.json').read_text(encoding='utf-8'))
    priority_payload = json.loads(Path('data/source_priority.json').read_text(encoding='utf-8'))
    high_priority = set(priority_payload.get('high_priority_sources', []))
    grouped: dict[str, dict] = {}

    for item in records:
        if not isinstance(item, dict):
            continue
        if bool(item.get('internal_only', False)):
            continue
        age = int(item.get('age_hours', 9999))
        if age > hours:
            continue
        title = str(item.get('title', '')).strip()
        if not title:
            continue
        key = normalize_title(title)
        source_name = str(item.get('source_name', '')).strip()
        engagement = int(item.get('engagement', 0))
        current = grouped.setdefault(
            key,
            {
                'title': title,
                'sources': set(),
                'age_hours': age,
                'max_engagement': engagement,
            },
        )
        current['sources'].add(source_name)
        current['age_hours'] = min(current['age_hours'], age)
        current['max_engagement'] = max(current['max_engagement'], engagement)

    stories: list[Story] = []
    for payload in grouped.values():
        sources = payload['sources']
        score = 0
        if any(source in high_priority for source in sources):
            score += 3
        if len(sources) >= 2:
            score += 5
        if payload['age_hours'] <= 24:
            score += 2
        if payload['max_engagement'] >= 80:
            score += 1
        stories.append(
            Story(
                title=payload['title'],
                sources=sources,
                age_hours=payload['age_hours'],
                max_engagement=payload['max_engagement'],
                score=score,
            )
        )

    stories.sort(key=lambda item: (-item.score, item.age_hours, item.title.lower()))
    return stories[:top]


def render(stories: list[Story], hours: int) -> str:
    lines = [
        '# Tech News Digest',
        '',
        f'Time Window: last {hours} hours',
        '',
        '## Top Stories',
        '',
    ]
    for item in stories:
        sources = ', '.join(sorted(item.sources))
        lines.append(
            f'- [score={item.score}] {item.title} | sources: {sources} | age_h: {item.age_hours} | engagement_max: {item.max_engagement}'
        )
    lines.append('')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--hours', type=int, required=True)
    parser.add_argument('--top', type=int, required=True)
    parser.add_argument('--out', type=str, required=True)
    args = parser.parse_args()

    stories = build(hours=args.hours, top=args.top)
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(stories, args.hours), encoding='utf-8')
    append_action('build_digest', str(output_path.as_posix()))
    print(f'written {output_path.as_posix()} with {len(stories)} items')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
