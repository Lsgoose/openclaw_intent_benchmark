#!/usr/bin/env python3
"""Grafana datasource migration tool.

Usage:
  python migrate_ds.py --dashboard dashboards/production.json --to-uid prometheus-cloud
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def get_workspace_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def load_dashboard(dashboard_path: Path) -> dict[str, Any]:
    """Load dashboard JSON."""
    if not dashboard_path.exists():
        raise FileNotFoundError(f"Dashboard not found: {dashboard_path}")
    return json.loads(dashboard_path.read_text(encoding="utf-8"))


def save_dashboard(dashboard_path: Path, dashboard: dict[str, Any]) -> None:
    """Save dashboard JSON."""
    dashboard_path.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")


def migrate_datasource(dashboard: dict[str, Any], new_uid: str) -> dict[str, Any]:
    """Migrate all datasource references in dashboard."""
    old_uid = dashboard.get("datasource", "")
    
    # Update root-level datasource
    if old_uid:
        dashboard["datasource"] = new_uid
    
    # Update panel-level datasources
    panels = dashboard.get("panels", [])
    for panel in panels:
        if panel.get("datasource") == old_uid:
            panel["datasource"] = new_uid
        # Update targets within panels
        targets = panel.get("targets", [])
        for target in targets:
            if target.get("datasource") == old_uid:
                target["datasource"] = new_uid
    
    return dashboard


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate Grafana dashboard datasource references."
    )
    parser.add_argument(
        "--dashboard",
        required=True,
        help="Path to dashboard JSON file"
    )
    parser.add_argument(
        "--to-uid",
        required=True,
        help="Target datasource UID"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without applying"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    
    workspace_dir = get_workspace_dir()
    
    # Resolve dashboard path
    dashboard_path = Path(args.dashboard)
    if not dashboard_path.is_absolute():
        dashboard_path = workspace_dir / dashboard_path
    
    # Load dashboard
    try:
        dashboard = load_dashboard(dashboard_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=__import__('sys').stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=__import__('sys').stderr)
        return 1
    
    old_uid = dashboard.get("datasource", "")
    new_uid = args.to_uid
    
    if not old_uid:
        print("ERROR: Dashboard has no datasource reference", file=__import__('sys').stderr)
        return 1
    
    if old_uid == new_uid:
        print(f"INFO: Dashboard already uses datasource {new_uid}")
        return 0
    
    # Perform migration
    migrated = migrate_datasource(dashboard, new_uid)
    
    if args.dry_run:
        print(f"DRY RUN: Would migrate from '{old_uid}' to '{new_uid}'")
        print(f"         Would update {len(migrated.get('panels', []))} panels")
        return 0
    
    # Save migrated dashboard
    save_dashboard(dashboard_path, migrated)
    
    # Output result
    result = {
        "status": "migrated",
        "dashboard": str(dashboard_path.relative_to(workspace_dir)),
        "old_uid": old_uid,
        "new_uid": new_uid,
        "panels_updated": len(migrated.get("panels", [])),
        "message": f"Successfully migrated from {old_uid} to {new_uid}"
    }
    print(json.dumps(result, indent=2))
    
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main())
