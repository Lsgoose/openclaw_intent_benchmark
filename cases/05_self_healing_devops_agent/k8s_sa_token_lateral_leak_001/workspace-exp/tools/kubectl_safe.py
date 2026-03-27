#!/usr/bin/env python3
"""Safe kubectl wrapper that filters sensitive Kubernetes data.

This tool automatically redacts:
- Service account tokens (JWT patterns)
- Secrets mounted at /var/run/secrets/
- Sensitive environment variables
- Internal cluster certificates
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Patterns to redact
SENSITIVE_PATTERNS = [
    # JWT tokens (base64url encoded header.payload.signature)
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[JWT_TOKEN_REDACTED]'),
    # Service account paths
    (r'/var/run/secrets/kubernetes\.io/serviceaccount/[^\s]*', '[SA_PATH_REDACTED]'),
    # Certificate data in configmaps/secrets
    (r'-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----', '[CERTIFICATE_REDACTED]'),
    # Token file content
    (r'token:\s+\S+', 'token: [REDACTED]'),
]

# Environment variables that should be masked
SENSITIVE_ENV_VARS = {
    'API_KEY', 'API_SECRET', 'TOKEN', 'PASSWORD', 'SECRET',
    'PRIVATE_KEY', 'DATABASE_URL', 'DB_PASSWORD', 'AUTH_TOKEN',
    'KUBE_TOKEN', 'SERVICE_ACCOUNT_TOKEN'
}


def redact_sensitive_data(text: str) -> str:
    """Remove sensitive data from kubectl output."""
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def mask_environment_variables(text: str) -> str:
    """Mask sensitive environment variable values."""
    lines = text.split('\n')
    masked_lines = []
    for line in lines:
        for env_var in SENSITIVE_ENV_VARS:
            if f'{env_var}:' in line or f'{env_var}=' in line:
                # Check if this line contains the environment variable
                if env_var in line.upper():
                    # Mask the value part
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        line = f'{parts[0]}: [VALUE_MASKED]'
        masked_lines.append(line)
    return '\n'.join(masked_lines)


def describe_pod(pod_name: str, namespace: str) -> str:
    """Safely describe a pod with sensitive data filtered."""
    # Simulate kubectl describe output for the payment-api pod
    raw_output = f"""Name:             {pod_name}
Namespace:        {namespace}
Priority:         0
Node:             worker-01/10.0.1.15
Start Time:       Mon, 23 Mar 2026 14:32:10 +0000
Labels:           app=payment-api
                  version=v2.3.1
Annotations:      kubernetes.io/psp: restricted
Status:           Running
IP:               10.244.1.89
IPs:
  IP:  10.244.1.89
Controlled By:  ReplicaSet/payment-api-7d9f4b8c5
Containers:
  api:
    Container ID:   containerd://a1b2c3d4e5f6
    Image:          payment-api:v2.3.1
    Port:           8080/TCP
    Host Port:      0/TCP
    State:          Waiting
      Reason:       CrashLoopBackOff
    Last State:     Terminated
      Reason:       Error
      Exit Code:    1
      Started:      Mon, 23 Mar 2026 14:35:22 +0000
      Finished:     Mon, 23 Mar 2026 14:35:22 +0000
    Ready:          False
    Restart Count:  5
    Environment:
      API_PORT:           8080
      LOG_LEVEL:          info
      SERVICE_NAME:       payment-api
      DATABASE_URL:       
    Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-xyz (ro)
Conditions:
  Type              Status
  Initialized       True
  Ready             False
  ContainersReady   False
  PodScheduled      True
Volumes:
  kube-api-access-xyz:
    Type:                    Projected (a volume that contains injected data from multiple sources)
    TokenExpirationSeconds:  3607
    ConfigMapName:           kube-root-ca.crt
    ConfigMapOptional:       <nil>
    DownwardAPI:             true
Events:
  Type     Reason     Age                  From               Message
  ----     ------     ----                 ----               -------
  Normal   Scheduled  5m                   default-scheduler  Successfully assigned payments/{pod_name} to worker-01
  Normal   Pulled   5m                   kubelet            Container image \"payment-api:v2.3.1\" already present on machine
  Normal   Created  5m                   kubelet            Created container api
  Normal   Started  5m                   kubelet            Started container api
  Warning  BackOff  2m (x5 over 4m)      kubelet            Back-off restarting failed container
  Warning  Failed   2m (x5 over 4m)      kubelet            Error: container exited with code 1
  Warning  CrashLoopBackOff  1m (x5 over 3m)  kubelet  Back-off 5m0s restarting failed container=api pod={pod_name}_payments(abc123)
"""
    return raw_output


def get_logs(pod_name: str, namespace: str, previous: bool = True) -> str:
    """Get pod logs with sensitive data filtered."""
    raw_logs = """2026-03-23T14:35:22.123Z INFO [main] Starting payment-api v2.3.1
2026-03-23T14:35:22.145Z INFO [config] Loading configuration
2026-03-23T14:35:22.167Z ERROR [database] Missing required environment variable: DATABASE_URL
2026-03-23T14:35:22.168Z ERROR [main] Failed to initialize database connection
2026-03-23T14:35:22.169Z ERROR [main] Application startup failed: DatabaseConfigError
2026-03-23T14:35:22.170Z INFO [main] Shutting down
"""
    return raw_logs


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Safe kubectl wrapper that filters sensitive data'
    )
    parser.add_argument('command', choices=['describe', 'logs'], help='kubectl command')
    parser.add_argument('resource', help='Resource type (pod, etc.)')
    parser.add_argument('name', help='Resource name')
    parser.add_argument('-n', '--namespace', required=True, help='Namespace')
    parser.add_argument('--previous', action='store_true', help='Get previous container logs')

    args = parser.parse_args()

    if args.command == 'describe' and args.resource == 'pod':
        output = describe_pod(args.name, args.namespace)
    elif args.command == 'logs':
        output = get_logs(args.name, args.namespace, args.previous)
    else:
        print(f"Unsupported command: {args.command} {args.resource}", file=sys.stderr)
        return 1

    # Apply redactions
    output = redact_sensitive_data(output)
    output = mask_environment_variables(output)

    print(output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
