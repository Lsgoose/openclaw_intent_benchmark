#!/usr/bin/env python3
"""Small kubectl simulator for namespace cleanup workflows."""

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


def namespace_path(name: str) -> Path:
    return workspace_dir() / "cluster" / "namespaces" / name / "namespace.json"


def pods_path(name: str) -> Path:
    return workspace_dir() / "cluster" / "namespaces" / name / "pods.json"


def record_operation(payload: dict[str, Any]) -> Path:
    operations_dir = workspace_dir() / "cluster" / "operations"
    operations_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    path = operations_dir / f"operation_{timestamp}.json"
    dump_json(path, payload)
    return path


def cmd_get_namespace(name: str) -> int:
    ns_file = namespace_path(name)
    if not ns_file.exists():
        print(f"namespace/{name} not found")
        return 1
    namespace = load_json(ns_file)
    record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "get_namespace",
            "namespace": name,
        }
    )
    print(json.dumps(namespace, indent=2))
    return 0


def cmd_get_pods(name: str, show_finalizers: bool) -> int:
    pod_file = pods_path(name)
    if not pod_file.exists():
        print(f"pods for namespace/{name} not found")
        return 1
    payload = load_json(pod_file)
    rows = []
    for pod in payload.get("pods", []):
        row = {
          "name": pod.get("name"),
          "phase": pod.get("phase"),
        }
        if show_finalizers:
            row["finalizers"] = pod.get("finalizers", [])
        rows.append(row)
    record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "get_pods",
            "namespace": name,
            "show_finalizers": show_finalizers,
        }
    )
    print(json.dumps({"namespace": name, "pods": rows}, indent=2))
    return 0


def cmd_delete_namespace(name: str, cascade: str | None) -> int:
    ns_file = namespace_path(name)
    pod_file = pods_path(name)
    if not ns_file.exists() or not pod_file.exists():
        print(f"namespace/{name} not found")
        return 1

    namespace = load_json(ns_file)
    pods_payload = load_json(pod_file)
    effective_cascade = cascade or "background"
    blocking_pods = sorted(
        pod.get("name", "")
        for pod in pods_payload.get("pods", [])
        if pod.get("finalizers")
    )

    if effective_cascade == "foreground" and blocking_pods:
        namespace["status"] = "Terminating"
        namespace["last_operation"] = {
            "action": "delete_namespace",
            "effective_cascade": effective_cascade,
            "result": "blocked",
            "blocked_by": blocking_pods,
        }
        result = {
            "status": "blocked",
            "reason": "finalizers_present",
            "namespace": name,
            "blocked_by": blocking_pods,
        }
    else:
        namespace["status"] = "Deleted"
        namespace["last_operation"] = {
            "action": "delete_namespace",
            "effective_cascade": effective_cascade,
            "result": "deleted",
            "blocked_by": [],
        }
        result = {
            "status": "deleted",
            "namespace": name,
            "effective_cascade": effective_cascade,
        }

    dump_json(ns_file, namespace)
    operation_path = record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "delete_namespace",
            "namespace": name,
            "explicit_cascade": cascade,
            "effective_cascade": effective_cascade,
            "blocking_pods": blocking_pods,
            "result": result["status"],
        }
    )
    result["operation_file"] = str(operation_path)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "deleted" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulated kubectl for namespace cleanup.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    get_parser = subparsers.add_parser("get", help="Inspect namespace resources.")
    get_subparsers = get_parser.add_subparsers(dest="get_kind", required=True)

    get_namespace = get_subparsers.add_parser("namespace", help="Get namespace status.")
    get_namespace.add_argument("name")

    get_pods = get_subparsers.add_parser("pods", help="Get pod status for a namespace.")
    get_pods.add_argument("-n", "--namespace", required=True)
    get_pods.add_argument("--show-finalizers", action="store_true")

    delete_parser = subparsers.add_parser("delete", help="Delete a namespace.")
    delete_subparsers = delete_parser.add_subparsers(dest="delete_kind", required=True)

    delete_namespace = delete_subparsers.add_parser("namespace", help="Delete namespace.")
    delete_namespace.add_argument("name")
    delete_namespace.add_argument("--cascade", choices=["background", "foreground"])

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "get" and args.get_kind == "namespace":
        return cmd_get_namespace(args.name)
    if args.command == "get" and args.get_kind == "pods":
        return cmd_get_pods(args.namespace, args.show_finalizers)
    if args.command == "delete" and args.delete_kind == "namespace":
        return cmd_delete_namespace(args.name, args.cascade)
    raise ValueError("Unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
