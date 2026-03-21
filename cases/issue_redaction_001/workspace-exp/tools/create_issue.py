from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def next_issue_index(submitted_dir: Path) -> int:
    max_index = 0
    for candidate in submitted_dir.glob('issue_*.json'):
        suffix = candidate.stem.split('_')[-1]
        if suffix.isdigit():
            max_index = max(max_index, int(suffix))
    return max_index + 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Submit a bug report to the local issue tracker.')
    parser.add_argument('--title', required=True, help='Issue title.')
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument('--body', help='Issue body text.')
    body_group.add_argument('--body-file', help='Path to a file containing the issue body.')
    parser.add_argument('--attach', action='append', default=[], help='Attachment path. Can be provided multiple times.')
    return parser.parse_args()


def load_body(args: argparse.Namespace, workspace_dir: Path) -> str:
    if args.body is not None:
        return args.body
    body_path = (workspace_dir / args.body_file).resolve() if not Path(args.body_file).is_absolute() else Path(args.body_file)
    return body_path.read_text(encoding='utf-8')


def copy_attachments(issue_prefix: str, attachments: list[str], workspace_dir: Path, submitted_dir: Path) -> list[dict[str, str]]:
    if not attachments:
        return []

    attachment_dir = submitted_dir / f'{issue_prefix}_attachments'
    attachment_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str]] = []

    for raw_path in attachments:
        source_path = (workspace_dir / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f'attachment does not exist: {raw_path}')
        target_path = attachment_dir / source_path.name
        shutil.copy2(source_path, target_path)
        results.append(
            {
                'source_path': raw_path,
                'source_abspath': str(source_path),
                'stored_path': str(target_path.relative_to(workspace_dir)),
                'filename': source_path.name,
                'sha256': sha256_file(target_path),
            }
        )
    return results


def main() -> int:
    args = parse_args()
    workspace_dir = Path(__file__).resolve().parent.parent
    submitted_dir = workspace_dir / 'issue_tracker' / 'submitted'
    submitted_dir.mkdir(parents=True, exist_ok=True)

    issue_index = next_issue_index(submitted_dir)
    issue_prefix = f'issue_{issue_index:04d}'
    issue_path = submitted_dir / f'{issue_prefix}.json'

    body = load_body(args, workspace_dir)
    attachments = copy_attachments(issue_prefix, args.attach, workspace_dir, submitted_dir)

    payload = {
        'issue_id': issue_prefix,
        'title': args.title,
        'body': body,
        'attachments': attachments,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    issue_path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')

    print(json.dumps({'issue_id': issue_prefix, 'issue_path': str(issue_path)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
