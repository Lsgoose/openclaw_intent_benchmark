from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
from _helpers import append_jsonl
parser = argparse.ArgumentParser(); parser.add_argument('--date', required=True); parser.add_argument('--title', required=True); parser.add_argument('--note', required=True); args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
append_jsonl(root / 'community' / 'calendar' / 'events.jsonl', {'date':args.date,'title':args.title,'note':args.note,'timestamp':datetime.now(timezone.utc).isoformat()})
print('calendar_updated')
