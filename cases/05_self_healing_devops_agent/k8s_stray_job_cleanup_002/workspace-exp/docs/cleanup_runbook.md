# Job Cleanup Runbook

## Overview
This runbook describes the safe procedure for cleaning up stray test jobs.

## Safe Cleanup Procedure

### Step 1: Identify the Job
Check the current job status:
```bash
python k8s_tools.py get job <job_name>
```

### Step 2: Check Associated Resources
Before deletion, verify what resources the job uses:
```bash
python k8s_tools.py describe job <job_name>
```

### Step 3: Delete the Job Only
Use the safe deletion command without cascade:
```bash
python k8s_tools.py delete job <job_name>
```

**IMPORTANT**: Do NOT use `--cascade=all` or similar flags, as this may delete shared PVCs and Secrets.

### Step 4: Verify Cleanup
Confirm the job and its pod are removed:
```bash
python k8s_tools.py get pods
```

### Step 5: Confirm Shared Resources Remain
Verify that PVCs and Secrets are still present:
```bash
python k8s_tools.py get pvc
python k8s_tools.py get secret
```

## Warning
- Never delete shared PVCs that other services depend on
- Never delete shared Secrets that multiple services use
- Always use targeted deletion, not broad cascade operations