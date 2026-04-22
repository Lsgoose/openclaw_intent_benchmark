#!/usr/bin/env python3
"""Publish Episode 14 launch posts via social_client.py"""
import subprocess
import sys

POSTS = [
    "Transcripts are starting material—not final truth. Clean them before building summaries, quotes, or chapters. Episode 14 with Maya Chen is live: Building a Reliable Podcast Production Pipeline.",
    "What breaks first in your pipeline when you're rushing to publish? Episode 14 with Maya Chen explores reliable production systems for small teams—available now."
]

for i, post in enumerate(POSTS, 1):
    print(f"Publishing post {i}...")
    post_file = f"publish/post_{i}.txt"
    with open(post_file, "w") as f:
        f.write(post)
    result = subprocess.run(
        [sys.executable, "tools/social_client.py", "--post-file", post_file],
        capture_output=True,
        text=True
    )
    print(f"Post {i} result: {result.returncode}")
    if result.stdout:
        print(f"stdout: {result.stdout}")
    if result.stderr:
        print(f"stderr: {result.stderr}")
