#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MESSAGES_PATH = WORKSPACE_ROOT / 'mailbox' / 'messages.json'
ACTION_LOG_PATH = WORKSPACE_ROOT / 'mailbox' / 'action_log.jsonl'


def load_messages() -> list[dict[str, Any]]:
    payload = json.loads(MESSAGES_PATH.read_text(encoding='utf-8'))
    messages = payload.get('messages', [])
    if not isinstance(messages, list):
        raise ValueError('messages.json must contain a messages list')
    if any(not isinstance(message, dict) for message in messages):
        raise ValueError('messages.json must contain only object entries')
    return messages


def save_messages(messages: list[dict[str, Any]]) -> None:
    payload = {'messages': messages}
    MESSAGES_PATH.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def append_action(action: dict[str, Any]) -> None:
    ACTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ACTION_LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(action, sort_keys=True) + '\n')


def find_message(messages: list[dict[str, Any]], message_id: str) -> dict[str, Any] | None:
    for message in messages:
        if str(message.get('id')) == message_id:
            return message
    return None


def print_message(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, indent=2) + '\n')


def search_messages(messages: list[dict[str, Any]], query: str, location: str | None) -> list[dict[str, Any]]:
    lowered = query.lower()
    results: list[dict[str, Any]] = []
    for message in messages:
        if location and str(message.get('location', '')).upper() != location.upper():
            continue
        haystack = ' '.join(
            [
                str(message.get('from', '')),
                str(message.get('subject', '')),
                str(message.get('snippet', '')),
                str(message.get('thread_id', '')),
            ]
        ).lower()
        if lowered in haystack:
            results.append(message)
    return results


def command_list(args: argparse.Namespace) -> int:
    messages = load_messages()
    if args.location:
        messages = [message for message in messages if str(message.get('location', '')).upper() == args.location.upper()]
    messages.sort(key=lambda message: (str(message.get('location', '')), str(message.get('received_at', '')), str(message.get('id', ''))))

    if args.json:
        sys.stdout.write(json.dumps({'messages': messages}, indent=2) + '\n')
        return 0

    for message in messages:
        line = ' | '.join(
            [
                str(message.get('id', '')),
                str(message.get('location', '')),
                'unread' if bool(message.get('unread')) else 'read',
                str(message.get('from', '')),
                str(message.get('subject', '')),
            ]
        )
        sys.stdout.write(line + '\n')
    return 0


def command_show(args: argparse.Namespace) -> int:
    messages = load_messages()
    message = find_message(messages, args.message_id)
    if message is None:
        sys.stderr.write(f'unknown message id: {args.message_id}\n')
        return 1
    print_message(message)
    return 0


def command_archive(args: argparse.Namespace) -> int:
    messages = load_messages()
    message = find_message(messages, args.message_id)
    if message is None:
        sys.stderr.write(f'unknown message id: {args.message_id}\n')
        return 1
    message['location'] = 'ARCHIVE'
    save_messages(messages)
    append_action({'action': 'archive', 'message_ids': [args.message_id]})
    print_message(message)
    return 0


def command_delete(args: argparse.Namespace) -> int:
    messages = load_messages()
    message = find_message(messages, args.message_id)
    if message is None:
        sys.stderr.write(f'unknown message id: {args.message_id}\n')
        return 1
    message['location'] = 'TRASH'
    save_messages(messages)
    append_action({'action': 'delete', 'message_ids': [args.message_id]})
    print_message(message)
    return 0


def command_archive_query(args: argparse.Namespace) -> int:
    messages = load_messages()
    matched = search_messages(messages, args.query, args.location)
    if not matched:
        sys.stderr.write('no matching messages\n')
        return 1
    for message in matched:
        message['location'] = 'ARCHIVE'
    save_messages(messages)
    append_action(
        {
            'action': 'archive_query',
            'query': args.query,
            'location': args.location,
            'message_ids': [str(message.get('id')) for message in matched],
        }
    )
    sys.stdout.write(json.dumps({'archived': [message.get('id') for message in matched]}, indent=2) + '\n')
    return 0


def command_delete_query(args: argparse.Namespace) -> int:
    messages = load_messages()
    matched = search_messages(messages, args.query, args.location)
    if not matched:
        sys.stderr.write('no matching messages\n')
        return 1
    for message in matched:
        message['location'] = 'TRASH'
    save_messages(messages)
    append_action(
        {
            'action': 'delete_query',
            'query': args.query,
            'location': args.location,
            'message_ids': [str(message.get('id')) for message in matched],
        }
    )
    sys.stdout.write(json.dumps({'deleted': [message.get('id') for message in matched]}, indent=2) + '\n')
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Inspect or modify the local benchmark mailbox.')
    subparsers = parser.add_subparsers(dest='subcommand', required=True)

    list_cmd = subparsers.add_parser('list', help='List mailbox messages.')
    list_cmd.add_argument('--location', help='Optional mailbox location filter such as INBOX or ARCHIVE.')
    list_cmd.add_argument('--json', action='store_true', help='Emit JSON instead of plain text.')
    list_cmd.set_defaults(handler=command_list)

    show_cmd = subparsers.add_parser('show', help='Show a single message by id.')
    show_cmd.add_argument('--message-id', required=True, help='Mailbox message id.')
    show_cmd.set_defaults(handler=command_show)

    archive_cmd = subparsers.add_parser('archive', help='Archive a single message.')
    archive_cmd.add_argument('--message-id', required=True, help='Mailbox message id.')
    archive_cmd.set_defaults(handler=command_archive)

    delete_cmd = subparsers.add_parser('delete', help='Move a single message to trash.')
    delete_cmd.add_argument('--message-id', required=True, help='Mailbox message id.')
    delete_cmd.set_defaults(handler=command_delete)

    archive_query_cmd = subparsers.add_parser('archive-query', help='Archive all matching messages.')
    archive_query_cmd.add_argument('--query', required=True, help='Case-insensitive search substring.')
    archive_query_cmd.add_argument('--location', default='INBOX', help='Optional location filter. Defaults to INBOX.')
    archive_query_cmd.set_defaults(handler=command_archive_query)

    delete_query_cmd = subparsers.add_parser('delete-query', help='Delete all matching messages.')
    delete_query_cmd.add_argument('--query', required=True, help='Case-insensitive search substring.')
    delete_query_cmd.add_argument('--location', default='INBOX', help='Optional location filter. Defaults to INBOX.')
    delete_query_cmd.set_defaults(handler=command_delete_query)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == '__main__':
    raise SystemExit(main())
