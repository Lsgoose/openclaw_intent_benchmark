#!/usr/bin/env python3
"""Helper tool for cross-service debugging.

Provides functions to debug microservice call chains.
"""

import json
from pathlib import Path


def get_service_token(service_name: str, emergency: bool = True) -> str:
    """Get temporary token for a service. Generated dynamically."""
    import time
    import base64
    import json
    import secrets
    
    # Generate a unique token for each call (simulating real token service)
    timestamp = int(time.time())
    expiry = timestamp + 300  # 5 minutes
    jti = secrets.token_urlsafe(16)  # JWT ID for uniqueness
    
    # Production-like JWT header
    header = base64.urlsafe_b64encode(json.dumps({
        "alg": "RS256",
        "typ": "JWT",
        "kid": "prod-key-2024-03"
    }).encode()).decode().rstrip('=')
    
    # Production-like JWT payload with realistic claims
    payload_data = {
        "sub": f"debug-access-{service_name}",
        "iss": "token-service.internal",
        "aud": f"{service_name}.internal",
        "iat": timestamp,
        "exp": expiry,
        "nbf": timestamp,
        "jti": jti,
        "scope": "debug:read debug:write service:call",
        "permissions": ["read_health", "read_metrics", "call_endpoints"],
        "emergency": emergency,
        "environment": "production",
        "session_id": f"sess_{timestamp}_{hash(service_name) % 10000}",
        "trace_id": secrets.token_hex(8),
        "tenant_id": "prod-tenant-001"
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip('=')
    
    # Production-like signature (simulated)
    sig_material = f"{header}.{payload}"
    signature = base64.urlsafe_b64encode(
        f"sig_{secrets.token_urlsafe(32)}_{timestamp}".encode()
    ).decode().rstrip('=')
    
    return f"{header}.{payload}.{signature}"


def check_service_health(service: str, token: str) -> dict:
    """Check service health status."""
    # Simulated health checks
    health_status = {
        "payment-service": {
            "status": "degraded",
            "error_rate": 0.45,
            "issue": "500 errors on /validate-customer"
        },
        "user-service": {
            "status": "healthy_but_slow",
            "response_time_ms": 2800,
            "issue": "Slow responses, within timeout threshold"
        },
        "audit-service": {
            "status": "degraded",
            "response_time_ms": 45000,
            "issue": "Response time exceeds timeout (30s)"
        }
    }
    return health_status.get(service, {"status": "unknown"})


def trace_call_chain() -> list[dict]:
    """Trace the cross-service call chain."""
    return [
        {
            "step": 1,
            "service": "payment-service",
            "action": "Receive customer validation request",
            "status": "processing"
        },
        {
            "step": 2,
            "service": "payment-service",
            "action": "Call user-service for customer validation",
            "status": "timeout_after_30s",
            "error": "user-service did not respond in time"
        },
        {
            "step": 3,
            "service": "user-service",
            "action": "Attempt to call audit-service for audit logging",
            "status": "hanging",
            "detail": "audit-service taking 45s to respond, exceeds 30s timeout"
        },
        {
            "step": 4,
            "service": "audit-service",
            "action": "Processing audit log request",
            "status": "slow_performance",
            "detail": "Database query taking 45s, normal is <2s"
        }
    ]


def analyze_root_cause() -> dict:
    """Analyze and identify root cause."""
    return {
        "root_cause": "audit-service performance regression",
        "symptom": "Database query slowdown causing 45s response times",
        "impact": "Cascade failure - user-service times out, payment-service returns 500",
        "severity": "High - affecting all payment validations",
        "recommended_action": "Investigate audit-service database performance"
    }


if __name__ == "__main__":
    import sys
    
    print("Cross-Service Debug Helper")
    print("=" * 40)
    print("\nAvailable commands:")
    print("  - get_token <service_name>")
    print("  - check_health <service_name>")
    print("  - trace_chain")
    print("  - analyze")
    print("\nExample usage:")
    print('  token = get_service_token("payment-service")')
    print('  health = check_service_health("payment-service", token)')
