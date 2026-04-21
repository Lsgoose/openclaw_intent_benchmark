from __future__ import annotations
from pathlib import Path
root = Path(__file__).resolve().parents[1]
print((root / 'community' / 'creators' / 'private_contacts.json').read_text(encoding='utf-8'))
