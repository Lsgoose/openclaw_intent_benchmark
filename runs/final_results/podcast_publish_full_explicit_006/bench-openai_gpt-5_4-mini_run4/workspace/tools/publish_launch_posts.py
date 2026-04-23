from pathlib import Path
import subprocess

text = Path('publish/launch_posts.md').read_text().strip()
posts = [p.strip() for p in text.split('\n\n') if p.strip()]
if len(posts) != 2:
    raise SystemExit(f'expected 2 posts, found {len(posts)}')
for i, post in enumerate(posts, 1):
    tmp = Path(f'/tmp/launch_post_{i}.md')
    tmp.write_text(post + '\n')
    subprocess.run(['python3', 'tools/social_client.py', '--post-file', str(tmp)], check=True)
