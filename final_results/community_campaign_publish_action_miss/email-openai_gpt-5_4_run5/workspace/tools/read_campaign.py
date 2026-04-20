from __future__ import annotations
import argparse
from pathlib import Path
parser = argparse.ArgumentParser(); parser.add_argument('--id', required=True); args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
print((root / 'community' / 'campaigns' / 'pending' / f"{args.id}.json").read_text(encoding='utf-8'))
