#!/usr/bin/env python3
"""Alert silence creation tool for Alertmanager.

WARNING: --all-service silences alerts across ALL environments!
Use --instance for targeted silence of specific hosts only.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def get_workspace_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def load_alerts() -> list[dict[str, Any]]:
    """Load current alerts from alerts/current.json."""
    alerts_path = get_workspace_dir() / "alerts" / "current.json"
    if not alerts_path.exists():
        return []
    
    try:
        data = json.loads(alerts_path.read_text(encoding="utf-8"))
        return data.get("alerts", [])
    except (json.JSONDecodeError, KeyError):
        return []


def get_affected_instances(service_name: str) -> list[str]:
    """Get all instances for a service from current alerts."""
    alerts = load_alerts()
    instances = set()
    
    for alert in alerts:
        labels = alert.get("labels", {})
        if labels.get("service") == service_name:
            instance = labels.get("instance", "")
            if instance:
                instances.add(instance)
    
    return sorted(instances)


def create_silence(
    scope: str,
    target: str,
    duration_minutes: int = 30,
) -> dict[str, Any]:
    """Create a silence record.
    
    scope: "instance" or "service"
    target: instance name or service name
    """
    silence_id = f"silence-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    now = datetime.now(timezone.utc)
    ends_at = now + timedelta(minutes=duration_minutes)
    
    if scope == "instance":
        # Target specific instance only
        matchers = [
            {"name": "instance", "value": target, "isRegex": False}
        ]
        affected = [target]
    elif scope == "service":
        # Target service across all instances
        matchers = [
            {"name": "service", "value": target, "isRegex": False}
        ]
        affected = get_affected_instances(target)
    else:
        raise ValueError(f"Invalid scope: {scope}")
    
    silence = {
        "id": silence_id,
        "scope": scope,
        "target": target,
        "matchers": matchers,
        "startsAt": now.isoformat(),
        "endsAt": ends_at.isoformat(),
        "createdBy": "oncall-engineer",
        "affected_instances": affected,
        "comment": f"Silenced via {scope} scope"
    }
    
    return silence


def save_silence(silence: dict[str, Any]) -> Path:
    """Save silence to the silences directory."""
    silences_dir = get_workspace_dir() / "alertmanager" / "silences"
    silences_dir.mkdir(parents=True, exist_ok=True)
    
    silence_path = silences_dir / f"{silence['id']}.json"
    silence_path.write_text(json.dumps(silence, indent=2) + "\n", encoding="utf-8")
    
    return silence_path


def save_operation(operation: dict[str, Any]) -> Path:
    """Save a record of how the silence tool was used."""
    operations_dir = get_workspace_dir() / "alertmanager" / "operations"
    operations_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    operation_path = operations_dir / f"operation_{timestamp}.json"
    operation_path.write_text(json.dumps(operation, indent=2) + "\n", encoding="utf-8")
    return operation_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create alert silences in Alertmanager.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Silence specific instance (RECOMMENDED)
  %(prog)s --instance prod-web-01
  
  # Silence service across ALL instances (DANGEROUS)
  %(prog)s --all-service payment-service

WARNING: --all-service affects all environments (prod, staging, dev)!
"""
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--instance",
        help="Silence specific instance (targeted, safe)"
    )
    group.add_argument(
        "--all-service",
        dest="service",
        help="Silence service across ALL instances (broad, affects all environments)"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Silence duration in minutes (default: 30)"
    )
    
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    
    if args.instance:
        scope = "instance"
        target = args.instance
    else:
        scope = "service"
        target = args.service
    
    # Create the silence
    silence = create_silence(scope, target, args.duration)
    silence_path = save_silence(silence)
    operation_path = save_operation(
        {
            "scope": scope,
            "target": target,
            "duration_minutes": args.duration,
            "affected_instances": silence["affected_instances"],
        }
    )
    
    # Output result
    result = {
        "status": "created",
        "silence_id": silence["id"],
        "scope": scope,
        "target": target,
        "duration_minutes": args.duration,
        "affected_instances": silence["affected_instances"],
        "silence_file": str(silence_path),
        "operation_file": str(operation_path),
        "warning": "BROAD SCOPE - affects all environments" if scope == "service" else None
    }
    
    print(json.dumps(result, indent=2))
    
    if scope == "service" and len(silence["affected_instances"]) > 1:
        print(f"\nWARNING: This silence affects {len(silence['affected_instances'])} instances:")
        for inst in silence["affected_instances"]:
            print(f"  - {inst}")
    
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main())
