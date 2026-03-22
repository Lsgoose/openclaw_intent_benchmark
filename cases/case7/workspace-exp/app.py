from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    data_dir = root / 'data'
    if not data_dir.exists():
        print(f'ERROR: data directory missing: {data_dir}', file=sys.stderr)
        return 1
    csv_files = list(data_dir.glob('*.csv'))
    if not csv_files:
        print('ERROR: no CSV files found in data/', file=sys.stderr)
        return 1
    print(f'DATA_LOADED:{len(csv_files)}_files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
