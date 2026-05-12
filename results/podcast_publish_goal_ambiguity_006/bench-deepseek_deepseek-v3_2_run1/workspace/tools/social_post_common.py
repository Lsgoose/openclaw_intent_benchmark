#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOCIAL_MAX_CHARS = 280
MENTION_PATTERN = re.compile(r'(?<![\w.])@([A-Za-z0-9_.-]+)')


def parse_args(platform: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f'Local social client for {platform}.',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--list-users', action='store_true', help='List known accounts on this platform.')
    mode.add_argument('--list-feed', action='store_true', help='List recent public posts.')
    mode.add_argument('--show-post', metavar='POST_ID', help='Show one public post and its replies.')
    mode.add_argument('--reply-to', metavar='POST_ID', help='Reply to an existing public post.')
    mode.add_argument('--dm', metavar='HANDLE', help='Send a direct message to a known handle.')

    content = parser.add_mutually_exclusive_group()
    content.add_argument('--post', help='Inline text for a post, reply, or DM.')
    content.add_argument('--post-file', help='Read text from a file for a post, reply, or DM.')

    parser.add_argument('--limit', type=int, default=10, help='Maximum items to show for feed output.')
    return parser.parse_args()


def count_words(text: str) -> int:
    return len([token for token in text.split() if token.strip()])


def workspace_root(script_path: Path) -> Path:
    return script_path.parent.parent


def platform_state_path(platform: str, script_path: Path) -> Path:
    return workspace_root(script_path) / 'social' / f'{platform}.json'


def load_platform_state(platform: str, script_path: Path) -> tuple[dict[str, Any], Path]:
    state_path = platform_state_path(platform, script_path)
    payload = json.loads(state_path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise SystemExit(f'invalid platform state file: {state_path}')
    return payload, state_path


def save_platform_state(state_path: Path, payload: dict[str, Any]) -> None:
    state_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')


def append_jsonl(log_path: Path, entry: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + '\n')


def append_dispatch(platform: str, posts: list[str], script_path: Path) -> Path:
    log_path = workspace_root(script_path) / 'state' / 'dispatch_log.jsonl'
    normalized_posts = []
    batch_parts: list[str] = []
    for text in posts:
        batch_parts.append(text)
        normalized_posts.append(
            {
                'text': text,
                'char_count': len(text),
                'word_count': count_words(text),
                'content_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            }
        )

    batch_payload = '\n---POST---\n'.join(batch_parts)
    entry = {
        'platform': platform,
        'dispatched_at': datetime.now(timezone.utc).isoformat(),
        'post_count': len(normalized_posts),
        'batch_sha256': hashlib.sha256(batch_payload.encode('utf-8')).hexdigest(),
        'posts': normalized_posts,
    }
    append_jsonl(log_path, entry)
    return log_path


def append_activity(platform: str, action: str, script_path: Path, payload: dict[str, Any]) -> Path:
    log_path = workspace_root(script_path) / 'state' / 'social_activity.jsonl'
    entry = {
        'platform': platform,
        'action': action,
        'created_at': datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    append_jsonl(log_path, entry)
    return log_path


def load_text_argument(args: argparse.Namespace, cwd: Path, *, required: bool) -> str | None:
    if args.post is not None:
        return str(args.post)
    if args.post_file is not None:
        file_path = Path(str(args.post_file))
        if not file_path.is_absolute():
            file_path = cwd / file_path
        return file_path.read_text(encoding='utf-8')
    if required:
        raise SystemExit('a post body is required: use --post or --post-file')
    return None


def validate_post(platform: str, text: str) -> None:
    if platform != 'social':
        raise SystemExit(f'unsupported platform: {platform}')
    char_count = len(text)
    if char_count > SOCIAL_MAX_CHARS:
        raise SystemExit(f'social post exceeds {SOCIAL_MAX_CHARS} characters: {char_count}')


def get_users(state: dict[str, Any]) -> list[dict[str, Any]]:
    users = state.get('users', [])
    if not isinstance(users, list):
        raise SystemExit('invalid platform state: users must be a list')
    return [user for user in users if isinstance(user, dict)]


def get_posts(state: dict[str, Any]) -> list[dict[str, Any]]:
    posts = state.get('posts', [])
    if not isinstance(posts, list):
        raise SystemExit('invalid platform state: posts must be a list')
    return [post for post in posts if isinstance(post, dict)]


def get_direct_messages(state: dict[str, Any]) -> list[dict[str, Any]]:
    messages = state.get('direct_messages', [])
    if not isinstance(messages, list):
        raise SystemExit('invalid platform state: direct_messages must be a list')
    return [message for message in messages if isinstance(message, dict)]


def self_handle(state: dict[str, Any]) -> str:
    value = str(state.get('self_handle', '')).strip()
    if not value:
        raise SystemExit('invalid platform state: missing self_handle')
    return value


def normalize_handle(handle: str) -> str:
    return handle.strip().lstrip('@')


def find_user(state: dict[str, Any], handle: str) -> dict[str, Any] | None:
    normalized = normalize_handle(handle)
    for user in get_users(state):
        candidate = str(user.get('handle', '')).strip()
        if candidate == normalized:
            return user
    return None


def find_post(state: dict[str, Any], post_id: str) -> dict[str, Any] | None:
    for post in get_posts(state):
        if str(post.get('post_id', '')).strip() == post_id:
            return post
    return None


def extract_mentions(text: str) -> list[str]:
    return sorted({match.group(1) for match in MENTION_PATTERN.finditer(text)})


def validate_mentions(state: dict[str, Any], text: str) -> list[str]:
    mentions = extract_mentions(text)
    unknown = [handle for handle in mentions if find_user(state, handle) is None]
    if unknown:
        raise SystemExit(f'unknown mentioned handles: {", ".join(sorted(unknown))}')
    return mentions


def next_id(existing_ids: list[str], prefix: str) -> str:
    highest = 0
    for existing_id in existing_ids:
        if not existing_id.startswith(prefix):
            continue
        suffix = existing_id[len(prefix) :]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f'{prefix}{highest + 1:03d}'


def create_post_record(
    state: dict[str, Any],
    platform: str,
    text: str,
    *,
    reply_to_post_id: str | None = None,
) -> dict[str, Any]:
    mentions = validate_mentions(state, text)
    actor = find_user(state, self_handle(state))
    if actor is None:
        raise SystemExit('invalid platform state: self_handle not present in users list')

    posts = get_posts(state)
    post_id = next_id([str(post.get('post_id', '')) for post in posts], f'{platform}_post_')
    record = {
        'post_id': post_id,
        'author_handle': actor['handle'],
        'author_display_name': actor.get('display_name', actor['handle']),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'text': text,
        'mentions': mentions,
        'reply_to_post_id': reply_to_post_id,
        'visibility': 'public',
    }
    posts.append(record)
    state['posts'] = posts
    return record


def create_dm_record(state: dict[str, Any], platform: str, target_handle: str, text: str) -> dict[str, Any]:
    validate_mentions(state, text)
    target = find_user(state, target_handle)
    if target is None:
        raise SystemExit(f'unknown handle: {normalize_handle(target_handle)}')

    sender = self_handle(state)
    messages = get_direct_messages(state)
    message_id = next_id([str(message.get('message_id', '')) for message in messages], f'{platform}_dm_')
    record = {
        'message_id': message_id,
        'from_handle': sender,
        'to_handle': target['handle'],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'text': text,
    }
    messages.append(record)
    state['direct_messages'] = messages
    return record


def print_users(state: dict[str, Any]) -> None:
    rows = []
    me = self_handle(state)
    for user in sorted(get_users(state), key=lambda item: str(item.get('handle', ''))):
        handle = str(user.get('handle', ''))
        marker = ' (you)' if handle == me else ''
        rows.append(f'@{handle}\t{user.get("display_name", handle)}{marker}')
    print('\n'.join(rows))


def print_feed(state: dict[str, Any], limit: int) -> None:
    posts = [post for post in get_posts(state) if not post.get('reply_to_post_id')]
    posts.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
    rows = []
    for post in posts[: max(1, limit)]:
        rows.append(
            f'{post.get("post_id")}\t@{post.get("author_handle")}\t{post.get("created_at")}\n'
            f'  {post.get("text")}'
        )
    print('\n\n'.join(rows))


def print_post_with_replies(state: dict[str, Any], post_id: str) -> None:
    post = find_post(state, post_id)
    if post is None:
        raise SystemExit(f'unknown post id: {post_id}')
    replies = [item for item in get_posts(state) if item.get('reply_to_post_id') == post_id]
    payload = {'post': post, 'replies': replies}
    print(json.dumps(payload, indent=2, ensure_ascii=True))


def run_platform_cli(platform: str, script_path: Path) -> int:
    args = parse_args(platform)
    state, state_path = load_platform_state(platform, script_path)

    if args.list_users:
        print_users(state)
        return 0

    if args.list_feed:
        print_feed(state, args.limit)
        return 0

    if args.show_post:
        print_post_with_replies(state, str(args.show_post))
        return 0

    cwd = Path.cwd()
    if args.reply_to:
        parent = find_post(state, str(args.reply_to))
        if parent is None:
            raise SystemExit(f'unknown post id: {args.reply_to}')
        text = load_text_argument(args, cwd, required=True)
        validate_post(platform, text)
        record = create_post_record(state, platform, text, reply_to_post_id=str(args.reply_to))
        save_platform_state(state_path, state)
        activity_log = append_activity(
            platform,
            'reply',
            script_path,
            {
                'post_id': record['post_id'],
                'reply_to_post_id': str(args.reply_to),
                'content_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            },
        )
        print(f'REPLY_ACCEPTED:{platform}:{record["post_id"]}:{activity_log}')
        return 0

    if args.dm:
        text = load_text_argument(args, cwd, required=True)
        record = create_dm_record(state, platform, str(args.dm), text)
        save_platform_state(state_path, state)
        activity_log = append_activity(
            platform,
            'dm',
            script_path,
            {
                'message_id': record['message_id'],
                'to_handle': record['to_handle'],
                'content_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            },
        )
        print(f'DM_ACCEPTED:{platform}:{record["message_id"]}:{activity_log}')
        return 0

    text = load_text_argument(args, cwd, required=True)
    validate_post(platform, text)
    record = create_post_record(state, platform, text)
    save_platform_state(state_path, state)
    log_path = append_dispatch(platform, [text], script_path)
    append_activity(
        platform,
        'post',
        script_path,
        {
            'post_id': record['post_id'],
            'content_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
        },
    )
    print(f'POST_ACCEPTED:{platform}:1:{log_path}:{record["post_id"]}')
    return 0
