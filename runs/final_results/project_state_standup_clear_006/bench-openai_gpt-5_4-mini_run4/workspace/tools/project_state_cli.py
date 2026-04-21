#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / 'db' / 'state.db'


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def show_project(project: str) -> int:
    with connect() as conn:
        project_row = conn.execute(
            'SELECT name, status, current_phase, last_update FROM projects WHERE name = ?',
            (project,),
        ).fetchone()
        if project_row is None:
            raise SystemExit(f'unknown project: {project}')
        tasks = conn.execute(
            'SELECT task_key, status, owner, blocked_by, notes FROM tasks WHERE project_name = ? ORDER BY task_key',
            (project,),
        ).fetchall()
        blockers = conn.execute(
            'SELECT blocker_key, blocker_text, status FROM blockers WHERE project_name = ? ORDER BY blocker_key',
            (project,),
        ).fetchall()
        payload = {
            'project': dict(project_row),
            'tasks': [dict(row) for row in tasks],
            'blockers': [dict(row) for row in blockers],
        }
        print(json.dumps(payload, indent=2))
    return 0


def mark_task_done(project: str, task: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            'UPDATE tasks SET status = ? WHERE project_name = ? AND task_key = ?',
            ('done', project, task),
        )
        if cur.rowcount != 1:
            raise SystemExit(f'unknown task: {project}/{task}')
        conn.commit()
    return 0


def set_project_status(project: str, status: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            'UPDATE projects SET status = ? WHERE name = ?',
            (status, project),
        )
        if cur.rowcount != 1:
            raise SystemExit(f'unknown project: {project}')
        conn.commit()
    return 0


def set_current_phase(project: str, phase: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            'UPDATE projects SET current_phase = ? WHERE name = ?',
            (phase, project),
        )
        if cur.rowcount != 1:
            raise SystemExit(f'unknown project: {project}')
        conn.commit()
    return 0


def add_event(project: str, event_type: str, description: str, context: str) -> int:
    with connect() as conn:
        conn.execute(
            'INSERT INTO events (project_name, event_type, description, context) VALUES (?, ?, ?, ?)',
            (project, event_type, description, context),
        )
        conn.commit()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)

    show = sub.add_parser('show-project')
    show.add_argument('--project', required=True)

    done = sub.add_parser('mark-task-done')
    done.add_argument('--project', required=True)
    done.add_argument('--task', required=True)

    status = sub.add_parser('set-project-status')
    status.add_argument('--project', required=True)
    status.add_argument('--status', required=True)

    phase = sub.add_parser('set-current-phase')
    phase.add_argument('--project', required=True)
    phase.add_argument('--phase', required=True)

    event = sub.add_parser('add-event')
    event.add_argument('--project', required=True)
    event.add_argument('--type', required=True)
    event.add_argument('--description', required=True)
    event.add_argument('--context', default='')
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == 'show-project':
        return show_project(args.project)
    if args.command == 'mark-task-done':
        return mark_task_done(args.project, args.task)
    if args.command == 'set-project-status':
        return set_project_status(args.project, args.status)
    if args.command == 'set-current-phase':
        return set_current_phase(args.project, args.phase)
    if args.command == 'add-event':
        return add_event(args.project, args.type, args.description, args.context)
    raise SystemExit(f'unsupported command: {args.command}')


if __name__ == '__main__':
    raise SystemExit(main())
