from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Write a feedback summary report.')
    parser.add_argument('--title', required=True, help='Report title.')
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument('--body', help='Report body text.')
    body_group.add_argument('--body-file', help='Path to a file containing the report body.')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_dir = Path(__file__).resolve().parent.parent
    reports_dir = workspace_dir / 'reports'
    reports_dir.mkdir(exist_ok=True)
    output_path = reports_dir / 'summary.txt'

    if args.body is not None:
        body = args.body
    else:
        body_path = (
            (workspace_dir / args.body_file).resolve()
            if not Path(args.body_file).is_absolute()
            else Path(args.body_file)
        )
        body = body_path.read_text(encoding='utf-8')

    content = (
        f'# {args.title}\n\n'
        f'Generated: {datetime.now(timezone.utc).isoformat()}\n\n'
        f'{body}\n'
    )
    output_path.write_text(content, encoding='utf-8')

    print(json.dumps({'report_path': str(output_path.relative_to(workspace_dir))}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
