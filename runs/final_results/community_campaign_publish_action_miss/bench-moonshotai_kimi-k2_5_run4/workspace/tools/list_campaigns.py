from __future__ import annotations
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
for f in sorted((root / 'community' / 'campaigns' / 'pending').glob('campaign_*.json')):
    p = json.loads(f.read_text(encoding='utf-8'))
    print(f"{p['campaign_id']} | status={p['status']} | title={p['title']}")
