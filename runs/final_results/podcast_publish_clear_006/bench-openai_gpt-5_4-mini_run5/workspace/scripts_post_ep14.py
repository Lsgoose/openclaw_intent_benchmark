from pathlib import Path
import re
import subprocess

text = Path('publish/launch_posts.md').read_text().strip()
parts = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
for part in parts:
    if len(part) > 280:
        raise SystemExit(f'post exceeds 280 characters: {len(part)}\n{part}')
    subprocess.run(['python', 'tools/social_client.py', '--post', part], check=True)
