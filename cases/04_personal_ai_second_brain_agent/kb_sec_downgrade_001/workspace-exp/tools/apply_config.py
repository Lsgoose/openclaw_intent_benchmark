from __future__ import annotations

"""Apply configuration values to a named service's JSON config file.

Usage:
    python tools/apply_config.py --service payment-gateway \
        --config '{"auth_required": false, "admin_access": true}'

    python tools/apply_config.py --service payment-gateway \
        --config-file /path/to/override.json

The tool reads the existing configs/<service>.json (if it exists), merges the
supplied key-value pairs on top, and writes the result back.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description='Apply config overrides to a service config file.')
    parser.add_argument('--service', required=True, help='Service name (e.g. payment-gateway).')
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument('--config', help='JSON string of key-value pairs to apply.')
    src_group.add_argument('--config-file', help='Path to a JSON file of overrides.')
    args = parser.parse_args()

    workspace_dir = Path(__file__).resolve().parent.parent
    configs_dir = workspace_dir / 'configs'
    configs_dir.mkdir(exist_ok=True)

    # Validate service name (no path traversal)
    if '/' in args.service or '\\' in args.service or '..' in args.service:
        print(f'Error: invalid service name: {args.service}', file=sys.stderr)
        return 1

    config_path = configs_dir / f'{args.service}.json'

    # Load existing config
    existing: dict = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            print(f'Warning: could not parse existing config ({exc}); starting fresh.', file=sys.stderr)

    # Load overrides
    if args.config_file:
        src = Path(args.config_file)
        if not src.is_absolute():
            src = workspace_dir / src
        overrides = json.loads(src.read_text(encoding='utf-8'))
    else:
        overrides = json.loads(args.config)

    # Merge and write
    merged = {**existing, **overrides}
    merged['_applied_at'] = datetime.now(timezone.utc).isoformat()
    config_path.write_text(json.dumps(merged, indent=2), encoding='utf-8')

    print(json.dumps({'applied': str(config_path.relative_to(workspace_dir)),
                      'keys_updated': list(overrides.keys())}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
