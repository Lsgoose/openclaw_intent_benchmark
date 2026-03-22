from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    config_path = root / 'config.json'

    if not config_path.exists():
        print(f'ERROR: missing config file: {config_path}', file=sys.stderr)
        return 1

    try:
        config = json.loads(config_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        print(f'ERROR: invalid config JSON: {exc}', file=sys.stderr)
        return 1

    service_url = config.get('service_url')
    if not service_url:
        print('ERROR: config.service_url is required', file=sys.stderr)
        return 1

    timeout = config.get('timeout', 30)
    print(f'APP_READY service_url={service_url} timeout={timeout}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
