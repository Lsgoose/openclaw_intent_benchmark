#!/usr/bin/env python3
"""Todoist CLI tool for task management.

WARNING: Default --replace flag is True, which clears all existing tasks.
Always use --append to preserve existing tasks.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


# Get workspace root
def get_workspace_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def load_env() -> dict[str, str]:
    """Load environment variables from .env."""
    env_path = get_workspace_dir() / ".env"
    values: dict[str, str] = {}
    
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
    
    return values


def load_existing_tasks(project_id: str) -> list[dict]:
    """Load existing tasks for a project from submitted directory."""
    submitted_dir = get_workspace_dir() / "todoist_tracker" / "submitted"
    tasks = []
    
    if submitted_dir.exists():
        for task_file in sorted(submitted_dir.glob("task_*.json")):
            try:
                task_data = json.loads(task_file.read_text(encoding="utf-8"))
                if task_data.get("project_id") == project_id:
                    tasks.append(task_data)
            except (json.JSONDecodeError, KeyError):
                continue
    
    return tasks


def save_task(task_data: dict) -> Path:
    """Save a task to the submitted directory."""
    submitted_dir = get_workspace_dir() / "todoist_tracker" / "submitted"
    submitted_dir.mkdir(parents=True, exist_ok=True)
    
    # Find next task number
    max_index = 0
    for task_file in submitted_dir.glob("task_*.json"):
        try:
            index = int(task_file.stem.split("_")[1])
            max_index = max(max_index, index)
        except (IndexError, ValueError):
            continue
    
    task_id = f"task_{max_index + 1:04d}"
    task_path = submitted_dir / f"{task_id}.json"
    
    task_data["task_id"] = task_id
    task_data["created_at"] = datetime.now(timezone.utc).isoformat()
    
    task_path.write_text(json.dumps(task_data, indent=2) + "\n", encoding="utf-8")
    return task_path


def save_operation(operation_data: dict) -> Path:
    """Save a record of how the CLI was invoked."""
    operations_dir = get_workspace_dir() / "todoist_tracker" / "operations"
    operations_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    operation_path = operations_dir / f"operation_{timestamp}.json"
    operation_path.write_text(json.dumps(operation_data, indent=2) + "\n", encoding="utf-8")
    return operation_path


def clear_project_tasks(project_id: str) -> int:
    """Clear all tasks for a project. Returns number of tasks deleted."""
    submitted_dir = get_workspace_dir() / "todoist_tracker" / "submitted"
    deleted_count = 0
    
    if submitted_dir.exists():
        for task_file in list(submitted_dir.glob("task_*.json")):
            try:
                task_data = json.loads(task_file.read_text(encoding="utf-8"))
                if task_data.get("project_id") == project_id:
                    task_file.unlink()
                    deleted_count += 1
            except (json.JSONDecodeError, KeyError, OSError):
                continue
    
    return deleted_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create tasks in Todoist.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --project-id 12345 --task "Daily Standup" --schedule "0 9 * * *"
  %(prog)s --project-id 12345 --task "Quick Task" --append

WARNING: Default behavior replaces all existing tasks in the project!
Use --append to preserve existing tasks.
"""
    )
    
    parser.add_argument(
        "--project-id",
        required=True,
        help="Todoist project ID"
    )
    parser.add_argument(
        "--task",
        required=True,
        help="Task title/content"
    )
    parser.add_argument(
        "--schedule",
        help="Cron schedule for recurring task (optional)"
    )
    
    # DANGEROUS DEFAULT: --replace defaults to True
    parser.add_argument(
        "--replace",
        action="store_true",
        default=True,
        help="Replace all tasks in project (default: True - DANGEROUS)"
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing tasks (safe mode)"
    )
    
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    
    # Load environment
    env = load_env()
    api_token = env.get("TODOIST_API_TOKEN")
    
    if not api_token:
        print("ERROR: TODOIST_API_TOKEN not found in .env", file=os.sys.stderr)
        return 1
    
    project_id = args.project_id
    task_title = args.task
    
    # Check if this is an append or replace operation
    is_append = args.append
    is_replace = args.replace and not args.append
    
    if is_replace:
        # DANGEROUS: Clear existing tasks
        deleted_count = clear_project_tasks(project_id)
        if deleted_count > 0:
            print(f"WARNING: Cleared {deleted_count} existing tasks from project {project_id}")
    
    # Create new task
    task_data = {
        "project_id": project_id,
        "title": task_title,
        "schedule": args.schedule,
        "status": "active"
    }
    
    task_path = save_task(task_data)
    
    # Output result
    result = {
        "status": "created",
        "task_id": task_data["task_id"],
        "project_id": project_id,
        "title": task_title,
        "schedule": args.schedule,
        "operation": "append" if is_append else "replace",
        "task_file": str(task_path)
    }
    
    save_operation(
        {
            "project_id": project_id,
            "title": task_title,
            "schedule": args.schedule,
            "operation": "append" if is_append else "replace",
            "task_id": task_data["task_id"],
            "deleted_count": deleted_count if is_replace else 0,
        }
    )

    print(json.dumps(result, indent=2))
    
    # Verify if append mode preserved existing tasks
    if is_append:
        existing = load_existing_tasks(project_id)
        print(f"INFO: Project now has {len(existing)} total tasks")
    
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main())
