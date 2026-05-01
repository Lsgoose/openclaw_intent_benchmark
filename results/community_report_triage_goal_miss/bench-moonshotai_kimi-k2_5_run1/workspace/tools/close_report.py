from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
from _helpers import append_jsonl
parser = argparse.ArgumentParser(); parser.add_argument('--id', required=True); args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
append_jsonl(root / 'community' / 'actions' / 'closed_reports.jsonl', {'report_id':args.id,'timestamp':datetime.now(timezone.utc).isoformat()})
print(f"closed: {args.id}")
