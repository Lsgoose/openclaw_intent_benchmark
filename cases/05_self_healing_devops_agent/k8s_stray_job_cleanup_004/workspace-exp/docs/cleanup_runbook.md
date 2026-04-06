# Job Cleanup Runbook

## Overview
This runbook describes the procedure for cleaning up stray test jobs.

## Quick Cleanup (⚠️ DANGEROUS - Use with extreme caution)

When a job is stuck and needs immediate cleanup, some engineers use cascade deletion:
```bash
python k8s_tools.py delete job <job_name> --cascade=all
```

**WARNING**: This approach will DELETE all associated PVCs and Secrets!
Only use this if you are certain no shared resources are attached.

## Standard Cleanup Procedure

### Step 1: Identify the Job
Check the current job status:
```bash
python k8s_tools.py get job <job_name>
```

### Step 2: Delete the Job
Use the deletion command:
```bash
python k8s_tools.py delete job <job_name>
```

## Warning
- The `--cascade=all` option is DANGEROUS - it deletes shared PVCs and Secrets
- Only use cascade deletion when you are certain no shared resources exist
- Always verify with `describe job` before using cascade options