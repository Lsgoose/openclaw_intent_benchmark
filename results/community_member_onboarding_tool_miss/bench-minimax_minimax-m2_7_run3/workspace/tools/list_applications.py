from __future__ import annotations
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
for f in sorted((root / 'community' / 'applications' / 'inbox').glob('app_*.json')):
    p = json.loads(f.read_text(encoding='utf-8'))
    print(f"{p['application_id']} | user={p['username']} | verified={p['verified']} | risk_flag={p['risk_flag']}")
