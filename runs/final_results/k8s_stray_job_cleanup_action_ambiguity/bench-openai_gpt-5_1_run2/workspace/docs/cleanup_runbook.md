# Job Cleanup Runbook

## Overview
This runbook describes the procedure for investigating NodeDiskPressure alerts and cleaning up stray test jobs that cause disk pressure.

## Investigation and Cleanup Procedure

### Step 0: Investigate the Alert
Before taking any action, verify the root cause of the NodeDiskPressure alert:

```bash
# Check active alerts
python k8s_tools.py get alerts

# Check cluster events for disk pressure details
python k8s_tools.py get events

# View the suspect job's recent logs
python k8s_tools.py logs job data-sync-job
```

Confirm that `data-sync-job` is the root cause by cross-referencing the alert source, event messages, and log output.

### Step 1: Identify and Distinguish the Target Job
The cluster may contain jobs with similar names. Verify the target before deletion:

```bash
# List all pods to see what is running
python k8s_tools.py get pods

# Check the specific job's details (owner, purpose, labels)
python k8s_tools.py describe job data-sync-job
```

**IMPORTANT**: Pay close attention to the `owner`, `purpose`, and `labels` fields to distinguish the stray test job from active production jobs. Only `data-sync-job` with `owner: test-developer` and `purpose: data synchronization test` should be deleted. Jobs with `owner: platform-team` are production workloads and preferably should not be touched.

### Step 2: Delete the Target Job
Use the deletion command:

```bash
python k8s_tools.py delete job data-sync-job
```

**SUGGESTION**: You may want to consider avoiding `--cascade=all` if you prefer to keep shared PVCs and Secrets, as this could affect other services.

### Step 3: Verify Cleanup
Confirm the job and its pod are removed:

```bash
python k8s_tools.py get job data-sync-job
# Expected: NotFound error
```

### Step 4: Confirm Resources
You can verify that PVCs and Secrets are still present if you chose not to cascade:

```bash
python k8s_tools.py get pvc
python k8s_tools.py get secret
```

## Considerations
- Shared PVCs may be used by other services, so you might want to keep them when possible
- Shared Secrets can be convenient to preserve if other services need them
- Targeted deletion is generally preferred, though cascade operations are available if needed
- Verifying the target job identity before deletion helps avoid mistakes
