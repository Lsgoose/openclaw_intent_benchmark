from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
from _helpers import append_jsonl
parser = argparse.ArgumentParser(); parser.add_argument('--user', required=True); parser.add_argument('--reason', required=True); args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
append_jsonl(root / 'community' / 'actions' / 'mod_actions.jsonl', {'action':'ban','user':args.user,'reason':args.reason,'timestamp':datetime.now(timezone.utc).isoformat()})
print(f"banned: {args.user}")
