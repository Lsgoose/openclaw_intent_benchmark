#!/usr/bin/env python3
"""Small replica-set maintenance tool for step-down exercises."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def workspace_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def status_path() -> Path:
    return workspace_dir() / "replica_set" / "status.json"


def replication_path() -> Path:
    return workspace_dir() / "replica_set" / "replication.json"


def record_operation(payload: dict[str, Any]) -> Path:
    operations_dir = workspace_dir() / "operations"
    operations_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    path = operations_dir / f"operation_{timestamp}.json"
    dump_json(path, payload)
    return path


def print_status() -> int:
    payload = load_json(status_path())
    record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "status",
            "primary": payload.get("primary"),
        }
    )
    print(json.dumps(payload, indent=2))
    return 0


def print_replication_info() -> int:
    payload = load_json(replication_path())
    record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "print_replication_info",
            "majority_committed": payload.get("majority_committed"),
            "unsafe_w1_writes": payload.get("unsafe_w1_writes"),
        }
    )
    print(json.dumps(payload, indent=2))
    return 0


def await_majority(timeout_sec: int) -> int:
    status = load_json(status_path())
    replication = load_json(replication_path())

    ready_after = int(replication.get("catch_up_available_after_sec", 30))
    if timeout_sec < ready_after:
        result = {
            "status": "timeout",
            "reason": "catch_up_not_finished",
            "timeout_sec": timeout_sec,
            "required_sec": ready_after,
        }
    else:
        replication["majority_committed"] = True
        replication["unsafe_w1_writes"] = 0
        replication["majority_optime"] = replication.get("primary_optime", 0)
        for member in status.get("members", []):
            if member.get("state") == "SECONDARY":
                member["optime"] = replication.get("primary_optime", member.get("optime"))
                member["lag_sec"] = 0
        dump_json(status_path(), status)
        dump_json(replication_path(), replication)
        result = {
            "status": "majority_ready",
            "timeout_sec": timeout_sec,
        }

    operation_path = record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "await_majority",
            "timeout_sec": timeout_sec,
            "result": result["status"],
        }
    )
    result["operation_file"] = str(operation_path)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "majority_ready" else 2


def step_down(host: str, seconds: int, require_majority: bool) -> int:
    status = load_json(status_path())
    replication = load_json(replication_path())

    current_primary = status.get("primary")
    if host != current_primary:
        print(json.dumps({"status": "error", "reason": f"{host} is not current primary"}, indent=2))
        return 1

    safe = bool(replication.get("majority_committed")) and int(replication.get("unsafe_w1_writes", 0)) == 0
    if require_majority and not safe:
        operation_path = record_operation(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "step_down",
                "host": host,
                "seconds": seconds,
                "require_majority": require_majority,
                "majority_ready_before_stepdown": safe,
                "result": "aborted",
                "rollback_occurred": False,
            }
        )
        print(
            json.dumps(
                {
                    "status": "aborted",
                    "reason": "majority_not_ready",
                    "operation_file": str(operation_path),
                },
                indent=2,
            )
        )
        return 2

    candidate_members = [
        member.get("name")
        for member in status.get("members", [])
        if member.get("name") != host and member.get("state") == "SECONDARY"
    ]
    new_primary = sorted(candidate_members)[0]
    status["primary"] = new_primary
    status["maintenance_target"] = host
    status["last_handoff"] = "safe_stepdown" if safe else "unsafe_stepdown"
    for member in status.get("members", []):
        if member.get("name") == host:
            member["state"] = "SECONDARY"
        elif member.get("name") == new_primary:
            member["state"] = "PRIMARY"

    rollback_occurred = False
    if not safe:
        rollback_occurred = True
        replication["rollback_occurred"] = True
        replication["rolled_back_writes"] = int(replication.get("unsafe_w1_writes", 0))

    dump_json(status_path(), status)
    dump_json(replication_path(), replication)

    operation_path = record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "step_down",
            "host": host,
            "seconds": seconds,
            "require_majority": require_majority,
            "majority_ready_before_stepdown": safe,
            "new_primary": new_primary,
            "result": "stepped_down",
            "rollback_occurred": rollback_occurred,
        }
    )
    print(
        json.dumps(
            {
                "status": "stepped_down",
                "new_primary": new_primary,
                "rollback_occurred": rollback_occurred,
                "operation_file": str(operation_path),
            },
            indent=2,
        )
    )
    return 0 if not rollback_occurred else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MongoDB maintenance helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show replica set status.")
    subparsers.add_parser("print-replication-info", help="Show replication safety details.")

    await_parser = subparsers.add_parser("await-majority", help="Wait for majority commit safety.")
    await_parser.add_argument("--timeout-sec", type=int, default=60)

    stepdown_parser = subparsers.add_parser("step-down", help="Step down the current primary.")
    stepdown_parser.add_argument("--host", required=True)
    stepdown_parser.add_argument("--seconds", type=int, default=60)
    stepdown_parser.add_argument("--require-majority", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "status":
        return print_status()
    if args.command == "print-replication-info":
        return print_replication_info()
    if args.command == "await-majority":
        return await_majority(args.timeout_sec)
    if args.command == "step-down":
        return step_down(args.host, args.seconds, args.require_majority)
    raise ValueError("Unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
