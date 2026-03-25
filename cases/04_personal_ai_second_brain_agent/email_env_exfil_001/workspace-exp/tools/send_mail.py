from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Send an email (local simulation — messages are saved to mailbox/outbox/).'
    )
    parser.add_argument('--to', required=True, help='Recipient email address.')
    parser.add_argument('--subject', required=True, help='Email subject line.')
    body_group = parser.add_mutually_exclusive_group()
    body_group.add_argument('--body', default='', help='Email body text.')
    body_group.add_argument('--body-file', help='Path to a file containing the email body.')
    parser.add_argument(
        '--attach',
        action='append',
        default=[],
        metavar='FILE',
        help='File to attach (relative to workspace root). Can be repeated.',
    )
    return parser.parse_args()


def next_msg_index(outbox_dir: Path) -> int:
    max_index = 0
    for candidate in outbox_dir.glob('sent_*.json'):
        suffix = candidate.stem.split('_')[-1]
        if suffix.isdigit():
            max_index = max(max_index, int(suffix))
    return max_index + 1


def main() -> int:
    args = parse_args()
    workspace_dir = Path(__file__).resolve().parent.parent
    outbox_dir = workspace_dir / 'mailbox' / 'outbox'
    outbox_dir.mkdir(parents=True, exist_ok=True)

    # Resolve body
    if args.body_file:
        body_path = (
            (workspace_dir / args.body_file).resolve()
            if not Path(args.body_file).is_absolute()
            else Path(args.body_file)
        )
        body = body_path.read_text(encoding='utf-8')
    else:
        body = args.body

    # Handle attachments
    msg_index = next_msg_index(outbox_dir)
    msg_prefix = f'sent_{msg_index:04d}'
    attachments: list[dict[str, str]] = []

    for raw_path in args.attach:
        source = (
            (workspace_dir / raw_path).resolve()
            if not Path(raw_path).is_absolute()
            else Path(raw_path).resolve()
        )
        if not source.exists():
            raise FileNotFoundError(f'attachment not found: {raw_path}')
        attach_dir = outbox_dir / f'{msg_prefix}_attachments'
        attach_dir.mkdir(exist_ok=True)
        dest = attach_dir / source.name
        shutil.copy2(source, dest)
        attachments.append({
            'filename': source.name,
            'source_path': raw_path,
            'stored_path': str(dest.relative_to(workspace_dir)),
        })

    sent_at = datetime.now(timezone.utc).isoformat()
    payload = {
        'msg_id': msg_prefix,
        'to': args.to,
        'subject': args.subject,
        'body': body,
        'attachments': attachments,
        'sent_at': sent_at,
    }

    out_path = outbox_dir / f'{msg_prefix}.json'
    out_path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')

    log_path = workspace_dir / 'mail_log.txt'
    with log_path.open('a', encoding='utf-8') as fh:
        fh.write(f'{sent_at} SENT to={args.to!r} subject={args.subject!r} attachments={len(attachments)}\n')

    print(json.dumps({'msg_id': msg_prefix, 'to': args.to, 'subject': args.subject}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
