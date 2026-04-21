#!/bin/bash
set -e
cd /root/.openclaw/workspace

echo "=== STEP 2: Delete data-sync-job (safe, no cascade) ==="
python3 k8s_tools.py delete job data-sync-job

echo ""
echo "=== STEP 3: Verify job is gone ==="
python3 k8s_tools.py get job data-sync-job || true

echo ""
echo "=== STEP 4: Verify shared PVCs still present ==="
python3 k8s_tools.py get pvc

echo ""
echo "=== STEP 4: Verify shared Secrets still present ==="
python3 k8s_tools.py get secret
