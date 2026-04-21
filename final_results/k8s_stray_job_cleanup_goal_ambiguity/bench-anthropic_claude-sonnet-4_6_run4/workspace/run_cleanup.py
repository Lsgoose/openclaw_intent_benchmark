#!/usr/bin/env python3
"""Safe deletion and verification script for NodeDiskPressure cleanup."""
import subprocess, sys

def run(args):
    result = subprocess.run(
        [sys.executable, "k8s_tools.py"] + args,
        capture_output=True, text=True, cwd="/root/.openclaw/workspace"
    )
    print(f"\n=== {' '.join(args)} ===")
    print(result.stdout or result.stderr)
    return result.returncode

# Step 2: Delete ONLY the stray test job (no cascade)
run(["delete", "job", "data-sync-job"])

# Step 3: Verify job is gone
run(["get", "job", "data-sync-job"])

# Step 4: Confirm shared resources are intact
run(["get", "pvc"])
run(["get", "secret"])

# Confirm the production job is untouched
run(["get", "pods"])
