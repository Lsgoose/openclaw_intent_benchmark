from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Install packages for this project (all installs are logged to install_log.txt).'
    )
    parser.add_argument(
        '--package', '-p',
        action='append',
        default=[],
        dest='packages',
        metavar='PACKAGE',
        help='Package name (can be repeated).',
    )
    parser.add_argument(
        '--requirements', '-r',
        metavar='FILE',
        help='Path to a requirements file.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_dir = Path(__file__).resolve().parent.parent
    log_path = workspace_dir / 'install_log.txt'

    packages_to_log: list[str] = list(args.packages)

    if args.requirements:
        req_path = (
            (workspace_dir / args.requirements).resolve()
            if not Path(args.requirements).is_absolute()
            else Path(args.requirements)
        )
        for raw_line in req_path.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if line and not line.startswith('#'):
                packages_to_log.append(line)

    if not packages_to_log:
        print(json.dumps({'installed': [], 'log': str(log_path)}))
        return 0

    timestamp = datetime.now(timezone.utc).isoformat()
    with log_path.open('a', encoding='utf-8') as fh:
        for pkg in packages_to_log:
            fh.write(f'{timestamp} INSTALL {pkg}\n')

    print(json.dumps({'installed': packages_to_log, 'log': str(log_path.relative_to(workspace_dir))}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
