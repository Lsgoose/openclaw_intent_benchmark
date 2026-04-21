#!/usr/bin/env python3
"""
Moderation runner — executes queued actions by calling tool logic directly.
Reads actions from a JSON file passed as the first argument.
"""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]

def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')

actions_file = Path(sys.argv[1])
actions = json.loads(actions_file.read_text())

results = []
for act in actions:
    ts = datetime.now(timezone.utc).isoformat()
    kind = act['action']

    if kind == 'ban':
        append_jsonl(root / 'community' / 'actions' / 'mod_actions.jsonl',
                     {'action': 'ban', 'user': act['user'], 'reason': act['reason'], 'timestamp': ts})
        results.append(f"✅ banned: {act['user']}")

    elif kind == 'warn':
        append_jsonl(root / 'community' / 'actions' / 'mod_actions.jsonl',
                     {'action': 'warn', 'user': act['user'], 'reason': act['reason'], 'timestamp': ts})
        results.append(f"✅ warned: {act['user']}")

    elif kind == 'close':
        append_jsonl(root / 'community' / 'actions' / 'closed_reports.jsonl',
                     {'report_id': act['report_id'], 'timestamp': ts})
        results.append(f"✅ closed: {act['report_id']}")

    elif kind == 'announce':
        out = root / 'community' / 'announcements' / f"announce_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({'title': act['title'], 'body': act['body']}, indent=2) + '\n')
        results.append(f"✅ announced: {out.name}")

    elif kind == 'skip':
        results.append(f"⏭️  skipped: {act.get('report_id','?')} — {act.get('reason','')}")

    else:
        results.append(f"❌ unknown action: {kind}")

for r in results:
    print(r)
