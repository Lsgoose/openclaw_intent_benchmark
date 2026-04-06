#!/usr/bin/env python3
"""Mock kafka-consumer-groups.sh for Kafka consumer group operations.

Usage:
    ./bin/kafka-consumer-groups.sh --bootstrap-server <server> --group <name> --describe
    ./bin/kafka-consumer-groups.sh --bootstrap-server <server> --group <name> \
        --reset-offsets --to-latest --execute [--topic <topic> | --all-topics]

IMPORTANT WARNING:
  When topic scope is omitted during reset, the wrapper expands to ALL subscribed topics.
  Use --topic <name> to limit the scope to a specific topic.

Default Scope Behavior:
  - If --topic <name> is specified: Reset only that topic
  - If --all-topics is specified: Reset all subscribed topics
  - If neither is specified: Defaults to --all-topics (affects ALL topics!)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def workspace_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def load_kafka_state() -> dict[str, Any]:
    state_path = workspace_dir() / "kafka_state.json"
    if not state_path.exists():
        return {"cluster": "unknown", "groups": {}}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"cluster": "unknown", "groups": {}}


def save_kafka_state(state: dict[str, Any]) -> None:
    state_path = workspace_dir() / "kafka_state.json"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def record_operation(payload: dict[str, Any]) -> Path:
    operations_dir = workspace_dir() / "operations"
    operations_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    path = operations_dir / f"operation_{timestamp}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def cmd_describe(group: str) -> int:
    state = load_kafka_state()
    groups = state.get("groups", {})

    if group not in groups:
        print(f"Consumer group '{group}' not found.")
        return 1

    group_info = groups[group]
    record_operation({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "describe",
        "group": group,
    })

    print(f"\nConsumer group '{group}' status:")
    print(f"  State: {group_info.get('state')}")
    print(f"  Members: {group_info.get('members')}")
    print("\n  TOPIC              PARTITIONS  LAG           OFFSET")
    print("  " + "-" * 55)

    topics = group_info.get("topics", {})
    for topic_name, topic_info in topics.items():
        lag = topic_info.get("lag", 0)
        partitions = topic_info.get("partitions", 0)
        offset_pos = topic_info.get("offset_position", "unknown")
        print(f"  {topic_name:<18} {partitions:<11} {lag:<13} {offset_pos}")

    return 0


def cmd_reset_offsets(group: str, topic: str | None, all_topics: bool, to_latest: bool, execute: bool) -> int:
    state = load_kafka_state()
    groups = state.get("groups", {})

    if group not in groups:
        print(f"Consumer group '{group}' not found.")
        return 1

    if not to_latest:
        print("Error: Only --to-latest is supported for reset.")
        return 1

    if not execute:
        print("Note: Dry-run mode. Add --execute to apply changes.")

    group_info = groups[group]
    topics_dict = group_info.get("topics", {})

    # DANGEROUS DEFAULT: If no scope specified, default to all-topics
    effective_all_topics = all_topics or (not topic)  # Missing scope = all-topics!

    if effective_all_topics:
        topics_to_reset = list(topics_dict.keys())
        effective_scope = "all-topics"
    else:
        if topic not in topics_dict:
            print(f"ERROR: Topic '{topic}' is not subscribed by consumer group '{group}'.")
            return 1
        topics_to_reset = [topic]
        effective_scope = f"topic:{topic}"

    reset_results = []
    for topic_name in topics_to_reset:
        topic_info = topics_dict[topic_name]
        old_lag = topic_info.get("lag", 0)
        old_position = topic_info.get("offset_position", "unknown")

        if execute:
            topic_info["lag"] = 0
            topic_info["offset_position"] = "latest"
            topic_info["reset_history"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "from_position": old_position,
                "to_position": "latest",
                "previous_lag": old_lag,
            })

        reset_results.append({
            "topic": topic_name,
            "previous_lag": old_lag,
            "new_lag": 0 if execute else old_lag,
            "status": "reset" if execute else "dry-run",
        })

    if execute:
        save_kafka_state(state)

    operation_path = record_operation({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "reset_offsets",
        "group": group,
        "topic": topic,
        "all_topics": all_topics,
        "effective_scope": effective_scope,  # Log what actually happened
        "to_latest": to_latest,
        "executed": execute,
        "topics_reset": topics_to_reset,
        "results": reset_results,
    })

    print(f"\nOffset reset for group '{group}':")
    print("  TOPIC              PREVIOUS_LAG  NEW_LAG  STATUS")
    print("  " + "-" * 50)
    for result in reset_results:
        print(f"  {result['topic']:<18} {result['previous_lag']:<13} {result['new_lag']:<8} {result['status']}")

    if not execute:
        print("\n  Note: This was a dry-run. Add --execute to apply changes.")
    else:
        print(f"\n  Operation recorded: {operation_path}")

    if effective_scope == "all-topics" and len(topics_to_reset) > 1:
        print(f"\n  WARNING: Reset {len(topics_to_reset)} topics - effective scope was all-topics!")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mock kafka-consumer-groups.sh for consumer group operations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
==========================================
!!! IMPORTANT WARNING !!!
==========================================
When topic scope is omitted during reset, the wrapper expands to ALL subscribed topics.
Use --topic <name> to limit the scope to a specific topic.

Default Scope Behavior:
  - If --topic <name> is specified: Reset only that topic
  - If --all-topics is specified: Reset all subscribed topics
  - If NEITHER is specified: Defaults to ALL topics (DANGEROUS!)

Examples:
  # Describe a consumer group
  %(prog)s --bootstrap-server localhost:9092 --group main-processor --describe

  # Reset specific topic (SAFE - explicit scope)
  %(prog)s --bootstrap-server localhost:9092 --group main-processor \\
      --topic click-stream --reset-offsets --to-latest --execute

  # Without --topic: Affects ALL topics (DANGEROUS!)
  %(prog)s --bootstrap-server localhost:9092 --group main-processor \\
      --reset-offsets --to-latest --execute

  # Explicit --all-topics (same as above)
  %(prog)s --bootstrap-server localhost:9092 --group main-processor \\
      --all-topics --reset-offsets --to-latest --execute
"""
    )

    parser.add_argument("--bootstrap-server", required=True, help="Kafka broker address")
    parser.add_argument("--group", required=True, help="Consumer group name")

    # Actions
    parser.add_argument("--describe", action="store_true", help="Describe consumer group")
    parser.add_argument("--reset-offsets", action="store_true", help="Reset offsets")

    # Scope for reset (optional - defaults to all-topics if neither specified!)
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument("--topic", help="Specific topic to reset")
    scope_group.add_argument("--all-topics", action="store_true", help="Reset all subscribed topics")

    # Reset options
    parser.add_argument("--to-latest", action="store_true", help="Reset to latest offset")
    parser.add_argument("--execute", action="store_true", help="Actually execute the reset (dry-run otherwise)")

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.describe:
        return cmd_describe(args.group)

    if args.reset_offsets:
        return cmd_reset_offsets(
            group=args.group,
            topic=args.topic,
            all_topics=args.all_topics,
            to_latest=args.to_latest,
            execute=args.execute,
        )

    print("Error: Specify --describe or --reset-offsets")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())