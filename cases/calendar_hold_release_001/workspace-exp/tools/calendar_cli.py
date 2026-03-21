#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = WORKSPACE_ROOT / 'calendar' / 'events.json'


def load_events() -> list[dict[str, Any]]:
    payload = json.loads(EVENTS_PATH.read_text(encoding='utf-8'))
    events = payload.get('events', [])
    if not isinstance(events, list):
        raise ValueError('events.json must contain an events list')
    if any(not isinstance(event, dict) for event in events):
        raise ValueError('events.json must contain only object entries')
    return events


def save_events(events: list[dict[str, Any]]) -> None:
    payload = {'events': events}
    EVENTS_PATH.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def find_event(events: list[dict[str, Any]], event_id: str) -> dict[str, Any] | None:
    for event in events:
        if str(event.get('id')) == event_id:
            return event
    return None


def print_event(event: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(event, indent=2) + '\n')


def command_list(args: argparse.Namespace) -> int:
    events = load_events()
    if args.date:
        events = [event for event in events if str(event.get('date')) == args.date]
    events.sort(key=lambda event: (str(event.get('date', '')), str(event.get('start', '')), str(event.get('id', ''))))

    if args.json:
        sys.stdout.write(json.dumps({'events': events}, indent=2) + '\n')
        return 0

    for event in events:
        line = ' | '.join(
            [
                str(event.get('id', '')),
                str(event.get('date', '')),
                f"{event.get('start', '')}-{event.get('end', '')}",
                str(event.get('status', '')),
                str(event.get('title', '')),
            ]
        )
        sys.stdout.write(line + '\n')
    return 0


def command_show(args: argparse.Namespace) -> int:
    events = load_events()
    event = find_event(events, args.event_id)
    if event is None:
        sys.stderr.write(f'unknown event id: {args.event_id}\n')
        return 1
    print_event(event)
    return 0


def command_cancel(args: argparse.Namespace) -> int:
    events = load_events()
    event = find_event(events, args.event_id)
    if event is None:
        sys.stderr.write(f'unknown event id: {args.event_id}\n')
        return 1

    event['status'] = 'cancelled'
    save_events(events)
    print_event(event)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Inspect or modify the local benchmark calendar.')
    subparsers = parser.add_subparsers(dest='subcommand', required=True)

    list_cmd = subparsers.add_parser('list', help='List events in the local calendar.')
    list_cmd.add_argument('--date', help='Optional YYYY-MM-DD filter.')
    list_cmd.add_argument('--json', action='store_true', help='Emit JSON instead of plain text.')
    list_cmd.set_defaults(handler=command_list)

    show_cmd = subparsers.add_parser('show', help='Show a single event by id.')
    show_cmd.add_argument('--event-id', required=True, help='Calendar event id.')
    show_cmd.set_defaults(handler=command_show)

    cancel_cmd = subparsers.add_parser('cancel', help='Cancel a single event by id.')
    cancel_cmd.add_argument('--event-id', required=True, help='Calendar event id.')
    cancel_cmd.set_defaults(handler=command_cancel)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == '__main__':
    raise SystemExit(main())
