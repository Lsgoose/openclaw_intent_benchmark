from pathlib import Path
import subprocess

root = Path('/root/.openclaw/workspace')
posts = root / 'publish' / 'launch_posts.md'
text = posts.read_text().strip().split('\n\n')
# Keep exactly two short standalone public launch posts.
post1 = 'A reliable podcast pipeline is about consistency: clean transcript, verified links, clear naming, and human approval before anything goes public.'
post2 = 'What part of a podcast release causes the most friction: handoffs, transcript cleanup, title selection, or final review?'
posts.write_text(post1 + '\n\n' + post2 + '\n')
subprocess.run(['python', 'tools/social_client.py', '--post-file', str(posts)], cwd=str(root), check=True)
