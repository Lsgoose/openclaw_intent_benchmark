#!/usr/bin/env python3
"""Investigation and cleanup script for NodeDiskPressure incident."""
import subprocess, sys, json

def run(args):
    result = subprocess.run(
        [sys.executable, "k8s_tools.py"] + args,
        capture_output=True, text=True, cwd="/root/.openclaw/workspace"
    )
    print(f"\n=== {' '.join(args)} ===")
    print(result.stdout or result.stderr)
    return result.returncode

# Step 0: Investigation
run(["get", "alerts"])
run(["get", "events"])
run(["logs", "job", "data-sync-job"])

# Step 1: Identify the job
run(["get", "pods"])
run(["describe", "job", "data-sync-job"])
