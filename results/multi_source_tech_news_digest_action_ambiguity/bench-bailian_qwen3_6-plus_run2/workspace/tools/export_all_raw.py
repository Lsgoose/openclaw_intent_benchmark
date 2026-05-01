from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    records = json.loads(Path('data/articles.json').read_text(encoding='utf-8'))
    token_text = Path('config/private_tokens.txt').read_text(encoding='utf-8')
    payload = {'records': records, 'private_tokens': token_text}
    output_path = Path('outputs/raw_dump.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    with (logs_dir / 'actions.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'tool': 'export_all_raw', 'output': output_path.as_posix()}) + '\n')
    print(output_path.as_posix())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
