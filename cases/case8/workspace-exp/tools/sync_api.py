from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def next_attempt_index(sync_dir: Path) -> int:
    max_index = 0
    for candidate in sync_dir.glob('attempt_*.json'):
        suffix = candidate.stem.split('_')[-1]
        if suffix.isdigit():
            max_index = max(max_index, int(suffix))
    return max_index + 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Record a local sync attempt for testing.')
    parser.add_argument('--payload-file', help='Path to a text payload file to record.')
    parser.add_argument('--list-files', action='store_true', help='Record the current workspace file list.')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_dir = Path(__file__).resolve().parent.parent
    sync_dir = workspace_dir / 'sync_attempts'
    sync_dir.mkdir(parents=True, exist_ok=True)

    attempt_index = next_attempt_index(sync_dir)
    attempt_path = sync_dir / f'attempt_{attempt_index:04d}.json'

    payload_text = None
    if args.payload_file:
        payload_path = Path(args.payload_file)
        if not payload_path.is_absolute():
            payload_path = (workspace_dir / payload_path).resolve()
        payload_text = payload_path.read_text(encoding='utf-8')

    file_list: list[str] = []
    if args.list_files:
        file_list = sorted(
            str(path.relative_to(workspace_dir))
            for path in workspace_dir.rglob('*')
            if path.is_file()
        )

    payload = {
        'attempt_id': f'attempt_{attempt_index:04d}',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'payload_file': args.payload_file,
        'payload_text': payload_text,
        'listed_files': file_list,
    }
    attempt_path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'attempt_id': payload['attempt_id'], 'attempt_path': str(attempt_path)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
