from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
from _helpers import append_jsonl
parser = argparse.ArgumentParser(); parser.add_argument('--id', required=True); parser.add_argument('--role', required=True); args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
append_jsonl(root / 'community' / 'members' / 'approved.jsonl', {'application_id':args.id,'role':args.role,'timestamp':datetime.now(timezone.utc).isoformat()})
print('approved')
