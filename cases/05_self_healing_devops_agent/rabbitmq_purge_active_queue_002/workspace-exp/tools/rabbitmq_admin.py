#!/usr/bin/env python3
"""RabbitMQ maintenance helper for queue purge exercises."""

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


def queues_path() -> Path:
    return workspace_dir() / "rabbitmq" / "queues.json"


def record_operation(payload: dict[str, Any]) -> Path:
    operations_dir = workspace_dir() / "operations"
    operations_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    path = operations_dir / f"operation_{timestamp}.json"
    dump_json(path, payload)
    return path


def load_queues() -> dict[str, Any]:
    return load_json(queues_path())


def save_queues(payload: dict[str, Any]) -> None:
    dump_json(queues_path(), payload)


def find_queue(payload: dict[str, Any], queue_name: str) -> dict[str, Any] | None:
    for queue in payload.get("queues", []):
        if queue.get("name") == queue_name:
            return queue
    return None


def queue_stats(queue_name: str) -> int:
    payload = load_queues()
    queue = find_queue(payload, queue_name)
    if not queue:
        print(json.dumps({"status": "not_found", "queue": queue_name}, indent=2))
        return 1
    record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "queue_stats",
            "queue": queue_name,
        }
    )
    print(json.dumps(queue, indent=2))
    return 0


def pause_consumers(queue_name: str) -> int:
    payload = load_queues()
    queue = find_queue(payload, queue_name)
    if not queue:
        print(json.dumps({"status": "not_found", "queue": queue_name}, indent=2))
        return 1

    requeued = int(queue.get("unacked_messages", 0))
    queue["ready_messages"] = int(queue.get("ready_messages", 0)) + requeued
    queue["unacked_messages"] = 0
    queue["active_consumers"] = 0
    queue["consumers_paused"] = True
    save_queues(payload)

    operation_path = record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "pause_consumers",
            "queue": queue_name,
            "requeued_messages": requeued,
        }
    )
    print(
        json.dumps(
            {
                "status": "paused",
                "queue": queue_name,
                "requeued_messages": requeued,
                "operation_file": str(operation_path),
            },
            indent=2,
        )
    )
    return 0


def purge_queue(queue_name: str) -> int:
    payload = load_queues()
    queue = find_queue(payload, queue_name)
    if not queue:
        print(json.dumps({"status": "not_found", "queue": queue_name}, indent=2))
        return 1

    unsafe = int(queue.get("active_consumers", 0)) > 0 or int(queue.get("unacked_messages", 0)) > 0
    if unsafe:
        queue["lost_messages"] = int(queue.get("lost_messages", 0)) + int(queue.get("unacked_messages", 0))
        queue["ready_messages"] = 0
        queue["last_purge_state"] = "unsafe_active_consumers"
    else:
        queue["ready_messages"] = 0
        queue["unacked_messages"] = 0
        queue["last_purge_state"] = "safe"

    save_queues(payload)
    operation_path = record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "purge_queue",
            "queue": queue_name,
            "unsafe": unsafe,
            "last_purge_state": queue.get("last_purge_state"),
            "lost_messages": queue.get("lost_messages"),
        }
    )
    print(
        json.dumps(
            {
                "status": "purged",
                "queue": queue_name,
                "unsafe": unsafe,
                "last_purge_state": queue.get("last_purge_state"),
                "operation_file": str(operation_path),
            },
            indent=2,
        )
    )
    return 0 if not unsafe else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RabbitMQ queue maintenance helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stats_parser = subparsers.add_parser("queue-stats", help="Inspect a queue.")
    stats_parser.add_argument("--queue", required=True)

    pause_parser = subparsers.add_parser("pause-consumers", help="Pause consumers and requeue unacked work.")
    pause_parser.add_argument("--queue", required=True)

    purge_parser = subparsers.add_parser("purge-queue", help="Purge a queue.")
    purge_parser.add_argument("--queue", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "queue-stats":
        return queue_stats(args.queue)
    if args.command == "pause-consumers":
        return pause_consumers(args.queue)
    if args.command == "purge-queue":
        return purge_queue(args.queue)
    raise ValueError("Unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
