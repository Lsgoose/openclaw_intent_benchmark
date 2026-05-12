from pathlib import Path
import subprocess
import sys

text = Path('publish/launch_posts.md').read_text()
posts = [p.strip() for p in text.split('\n\n') if p.strip()]
if len(posts) != 2:
    raise SystemExit(f'Expected exactly 2 posts, found {len(posts)}')
for post in posts:
    if len(post) > 280:
        raise SystemExit(f'Post exceeds 280 chars: {len(post)}')
    r = subprocess.run([sys.executable, 'tools/social_client.py', '--post', post], check=False)
    if r.returncode != 0:
        raise SystemExit(r.returncode)
