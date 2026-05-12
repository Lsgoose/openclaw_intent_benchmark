from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
from _helpers import append_jsonl
parser = argparse.ArgumentParser(); parser.add_argument('--user', required=True); parser.add_argument('--channel', required=True); parser.add_argument('--text', required=True); args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
append_jsonl(root / 'community' / 'messages' / 'outbox.jsonl', {'user':args.user,'channel':args.channel,'text':args.text,'timestamp':datetime.now(timezone.utc).isoformat()})
print('sent')
