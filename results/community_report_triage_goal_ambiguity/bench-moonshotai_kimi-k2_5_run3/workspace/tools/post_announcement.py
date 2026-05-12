from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
parser = argparse.ArgumentParser(); parser.add_argument('--title', required=True); parser.add_argument('--body', required=True); args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
out = root / 'community' / 'announcements' / f"announce_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
out.write_text(json.dumps({'title': args.title, 'body': args.body}, indent=2) + '\n', encoding='utf-8')
print(str(out))
