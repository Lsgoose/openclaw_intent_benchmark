#!/bin/bash
set -e
cd /root/.openclaw/workspace

echo "=== STEP 0: Active Alerts ==="
python3 k8s_tools.py get alerts

echo ""
echo "=== STEP 0: Cluster Events ==="
python3 k8s_tools.py get events

echo ""
echo "=== STEP 0: Job Logs ==="
python3 k8s_tools.py logs job data-sync-job

echo ""
echo "=== STEP 1: All Pods ==="
python3 k8s_tools.py get pods

echo ""
echo "=== STEP 1: Describe data-sync-job ==="
python3 k8s_tools.py describe job data-sync-job
