#!/usr/bin/env python3
"""Helper tool to check webhook signatures safely.

This tool helps diagnose webhook signature issues without exposing secrets.
"""

import hmac
import hashlib
import json
from pathlib import Path


def verify_signature(webhook_secret: str, timestamp: str, body: str, expected_sig: str) -> bool:
    """Verify webhook signature."""
    payload = f"{timestamp}.{body}"
    computed = hmac.new(
        webhook_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={computed}", expected_sig)


def analyze_webhook(filepath: str) -> dict:
    """Analyze a webhook request for common signature issues."""
    data = json.loads(Path(filepath).read_text())
    
    issues = []
    
    # Check timestamp
    headers = data["request"]["headers"]
    timestamp = headers.get("x-timestamp", "0")
    current_time = 1711270200  # Simulated current time
    time_diff = abs(current_time - int(timestamp))
    
    if time_diff > 300:  # 5 minutes
        issues.append(f"Timestamp out of window: {time_diff}s old (max 300s)")
    
    # Check signature format
    sig = headers.get("x-signature", "")
    if not sig.startswith("sha256="):
        issues.append("Signature missing sha256= prefix")
    
    # Check API key presence
    api_key = headers.get("x-api-key", "")
    if not api_key:
        issues.append("Missing x-api-key header")
    
    return {
        "event_type": data.get("type"),
        "timestamp_valid": time_diff <= 300,
        "has_signature": bool(sig),
        "issues_found": issues,
        "recommendation": "Check webhook secret and timestamp window"
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python signature_checker.py <webhook_file>")
        sys.exit(1)
    
    result = analyze_webhook(sys.argv[1])
    print(json.dumps(result, indent=2))
