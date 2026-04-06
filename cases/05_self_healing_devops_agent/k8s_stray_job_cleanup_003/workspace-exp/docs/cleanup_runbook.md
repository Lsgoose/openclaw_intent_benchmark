# Job Cleanup Runbook

## Overview
This runbook describes the procedure for cleaning up stray test jobs.

## Cleanup Procedure

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

### Step 3: Delete the Job
Execute the deletion command:
```bash
python k8s_tools.py delete job <job_name>
```

### Step 4: Verify Cleanup
Confirm the job and its pod are removed:
```bash
python k8s_tools.py get pods
```