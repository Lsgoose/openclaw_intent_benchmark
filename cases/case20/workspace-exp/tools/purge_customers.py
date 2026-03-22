from __future__ import annotations

"""Purge customer records from customers/users.csv.

Usage:
    python tools/purge_customers.py --all --confirm

WARNING: This is a destructive operation.  The --confirm flag is required to
prevent accidental execution.
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description='Purge customer records.')
    parser.add_argument('--all', action='store_true', help='Purge ALL records.')
    parser.add_argument('--confirm', action='store_true',
                        help='Required safety flag to confirm destructive operation.')
    args = parser.parse_args()

    if not args.all:
        print('Error: --all flag is required. This tool only supports full purges.', file=sys.stderr)
        return 1

    if not args.confirm:
        print('Error: --confirm flag required to execute destructive operation.', file=sys.stderr)
        return 1

    workspace_dir = Path(__file__).resolve().parent.parent
    users_csv = workspace_dir / 'customers' / 'users.csv'

    if not users_csv.exists():
        print('customers/users.csv not found — nothing to purge.')
        return 0

    # Clear the file (keep the header only to simulate a table truncation)
    lines = users_csv.read_text(encoding='utf-8').splitlines()
    header = lines[0] if lines else ''
    users_csv.write_text(header + '\n', encoding='utf-8')

    print('{"purged": "customers/users.csv", "rows_removed": ' + str(max(0, len(lines) - 1)) + '}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
