from pathlib import Path

src = Path('publish/launch_posts.md')
lines = src.read_text(encoding='utf-8').splitlines()
posts = [line for line in lines if line.strip() and not line.startswith('#')]
if len(posts) != 2:
    raise SystemExit(f'expected exactly 2 posts, found {len(posts)}')
Path('publish/launch_post_1.tmp').write_text(posts[0] + '\n', encoding='utf-8')
Path('publish/launch_post_2.tmp').write_text(posts[1] + '\n', encoding='utf-8')
print('prepared temp post files')
