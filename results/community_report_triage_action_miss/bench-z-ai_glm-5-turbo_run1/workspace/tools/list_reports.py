from __future__ import annotations
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
for path in sorted((root / 'community' / 'reports' / 'inbox').glob('report_*.json')):
    p = json.loads(path.read_text(encoding='utf-8'))
    print(f"{p['report_id']} | user={p['reported_user']} | severity={p['severity']} | category={p['category']}")
