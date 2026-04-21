from __future__ import annotations
from pathlib import Path
root = Path(__file__).resolve().parents[1]
print((root / 'members' / 'private_directory.json').read_text(encoding='utf-8'))
