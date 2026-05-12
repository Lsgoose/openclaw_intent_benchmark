from __future__ import annotations
import argparse, json
from pathlib import Path
parser = argparse.ArgumentParser(); parser.add_argument('--id', required=True); args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
src = root / 'community' / 'campaigns' / 'pending' / f"{args.id}.json"
payload = json.loads(src.read_text(encoding='utf-8'))
out = root / 'community' / 'campaigns' / 'published' / f"{args.id}.md"
out.write_text(f"# {payload['title']}\n\n{payload['publish_body']}\n", encoding='utf-8')
print(str(out))
