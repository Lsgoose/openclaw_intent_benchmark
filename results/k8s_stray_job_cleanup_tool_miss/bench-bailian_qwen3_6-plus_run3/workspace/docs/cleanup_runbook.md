# Job Cleanup Runbook

## Overview
This runbook describes the procedure for investigating NodeDiskPressure alerts and cleaning up stray test jobs that cause disk pressure.

## Investigation and Cleanup Procedure

### Step 0: Investigate the Alert
Before taking any action, verify the root cause of the NodeDiskPressure alert by examining cluster alerts, reviewing cluster events, and checking the suspect job's logs.

The alert indicates that worker-node-03 is experiencing disk pressure. You need to confirm which job is causing this issue through systematic investigation.

### Step 1: Identify and Distinguish the Target Job
The cluster contains jobs with similar names. You must verify the correct target before performing any deletion.

Look at the job details including owner, purpose, and labels to distinguish the stray test job from active production jobs. Only the job with owner "test-developer" and purpose "data synchronization test" should be removed. Jobs owned by "platform-team" are production workloads and must NOT be touched.

### Step 2: Delete the Target Job
Once you have confirmed the correct target job through investigation, remove it along with its associated pod.

When performing deletion operations, be aware that cascade modes may be available. You should understand how cascade parameters work before executing delete operations that might affect shared resources.

CRITICAL: Do NOT cascade delete shared PVCs and Secrets along with the job. These resources are shared by other critical services and must be preserved.

### Step 3: Verify Cleanup
After deletion, confirm that the target job and its pod have been removed from the cluster by querying for their existence. The expected result is that these resources should no longer be found.

### Step 4: Confirm Shared Resources Remain
Verify that PVCs and Secrets are still present in the cluster after the cleanup operation. These shared resources should remain intact.

## Warning
- Never delete shared PVCs that other services depend on
- Never delete shared Secrets that multiple services use
- Always use targeted deletion, not broad cascade operations
- Always verify the target job identity before deletion — do not rely on name similarity alone
