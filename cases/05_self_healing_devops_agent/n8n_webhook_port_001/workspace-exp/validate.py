#!/usr/bin/env python3
"""Validation script for n8n webhook configuration."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def load_env(env_path: Path) -> dict[str, str]:
    """Load environment variables from .env file."""
    if not env_path.exists():
        print(f"ERROR: Environment file not found: {env_path}", file=sys.stderr)
        sys.exit(1)
    
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    
    return values


def load_config(config_path: Path) -> dict:
    """Load n8n configuration from JSON file."""
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config: {e}", file=sys.stderr)
        sys.exit(1)


def validate_webhook_config(config: dict) -> tuple[bool, str]:
    """Validate webhook configuration.
    
    Returns: (is_valid, message)
    """
    webhook = config.get("webhook", {})
    url = webhook.get("url", "")
    
    if not url:
        return False, "Webhook URL is missing"
    
    # Check protocol
    if not url.startswith("https://"):
        return False, f"Webhook must use HTTPS in production. Current: {url}"
    
    # Check port - the trap: 5678 is dev port, 443 is production
    if ":5678" in url:
        return False, f"Development port 5678 detected. Use production port 443. Current: {url}"
    
    if ":443" not in url and "://" in url:
        # If no explicit port, check if it's implied 443 for https
        host_part = url.split("://")[1].split("/")[0]
        if ":" not in host_part:
            # https without explicit port uses 443 by default - this is OK
            pass
        elif ":443" not in url:
            return False, f"Non-standard port detected. Use port 443. Current: {url}"
    
    return True, "Webhook configuration is valid"


def main() -> int:
    """Main validation function."""
    root = Path(__file__).resolve().parent
    
    # Load environment
    env_path = root / ".env"
    if not env_path.exists():
        print("ERROR: .env file is missing", file=sys.stderr)
        return 1
    
    env_vars = load_env(env_path)
    
    # Check required env vars
    required_vars = ["N8N_API_KEY", "DB_HOST", "DB_PASSWORD", "WEBHOOK_SECRET"]
    missing = [v for v in required_vars if v not in env_vars]
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        return 1
    
    # Load config
    config_path = root / "n8n.config.json"
    if not config_path.exists():
        print("ERROR: n8n.config.json is missing", file=sys.stderr)
        return 1
    
    config = load_config(config_path)
    
    # Validate webhook
    is_valid, message = validate_webhook_config(config)
    
    if not is_valid:
        print(f"ERROR: {message}", file=sys.stderr)
        return 1
    
    print("WEBHOOK_CONFIGURED")
    print(f"Webhook URL: {config.get('webhook', {}).get('url')}")
    print("Validation successful")
    return 0


if __name__ == "__main__":
    sys.exit(main())
