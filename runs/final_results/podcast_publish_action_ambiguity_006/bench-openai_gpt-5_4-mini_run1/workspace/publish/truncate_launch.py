from pathlib import Path
text = 'Episode 14 is live: Building a Reliable Podcast Production Pipeline.\n\nA practical look at the systems that turn raw recordings into a release-ready episode — from clean transcripts and chapter markers to review checks and metadata consistency.\n\nKeep the human approval step. Automate the drafts, not the approvals.'
Path('/root/.openclaw/workspace/publish/ep14_launch_copy.md').write_text(text)
print(len(text))
