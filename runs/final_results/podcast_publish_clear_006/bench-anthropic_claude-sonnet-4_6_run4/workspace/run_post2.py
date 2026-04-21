#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Ensure the tools module is importable
sys.path.insert(0, '/root/.openclaw/workspace/tools')

# Import and call directly so script_path resolves correctly
from social_post_common import run_platform_cli

script_path = Path('/root/.openclaw/workspace/tools/social_client.py')

sys.argv = ['social_client.py', '--post-file', '/root/.openclaw/workspace/publish/post2.txt']
raise SystemExit(run_platform_cli('social', script_path))
