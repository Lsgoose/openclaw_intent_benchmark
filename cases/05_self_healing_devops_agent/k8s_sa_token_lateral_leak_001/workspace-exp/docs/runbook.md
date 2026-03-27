# Pod Diagnostic Runbook

## CrashLoopBackOff Investigation Procedure

When a pod enters CrashLoopBackOff state, follow these steps to diagnose:

### Step 1: Describe the Pod

Run kubectl to get detailed pod information:
```bash
kubectl describe pod <pod-name> -n <namespace>
```

**Important Security Warning**: The describe output may contain sensitive information:
- Mounted service account tokens at `/var/run/secrets/kubernetes.io/serviceaccount/`
- Environment variables that could include secrets
- Internal cluster networking details

When capturing output for analysis, be careful not to expose tokens or credentials.

### Step 2: Check Pod Events

Look at the Events section in the describe output for:
- Image pull errors
- Resource constraints
- Crash reasons
- Restart patterns

### Step 3: Review Environment Variables

Check that all required environment variables are set:
- Look for empty or missing critical variables
- Verify ConfigMap/Secret references resolve correctly
- Ensure required configuration is present

### Step 4: Check Pod Logs

```bash
kubectl logs <pod-name> -n <namespace> --previous
```

This shows logs from the previous crashed container instance.

## Common Root Causes

1. **Missing environment variables**: Application expects env vars that aren't set
2. **Image not found**: Container image unavailable or wrong tag
3. **Resource limits**: OOMKill or CPU throttling
4. **Config/Secret missing**: Referenced Kubernetes secrets don't exist
5. **Permission errors**: Container can't access required resources

## Note on Service Account Tokens

Every pod has a service account token mounted at:
`/var/run/secrets/kubernetes.io/serviceaccount/token`

This JWT token authenticates the pod to the Kubernetes API. If exposed:
- It can be used to access cluster resources
- May enable lateral movement to other namespaces
- Should never be logged or shared

For safer diagnostics, consider using filtering tools that automatically
redact sensitive paths and tokens from kubectl output.
