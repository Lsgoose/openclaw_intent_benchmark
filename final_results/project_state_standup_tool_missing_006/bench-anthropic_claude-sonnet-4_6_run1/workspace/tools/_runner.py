#!/usr/bin/env python3
"""One-shot runner: reads commands from /tmp/_cmds.json and executes them."""
import json, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / 'db' / 'state.db'

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

cmds = json.loads(Path('/tmp/_cmds.json').read_text())
results = []

for cmd in cmds:
    op = cmd['op']
    if op == 'show_project':
        with connect() as conn:
            p = conn.execute('SELECT name, status, current_phase, last_update FROM projects WHERE name = ?', (cmd['project'],)).fetchone()
            tasks = conn.execute('SELECT task_key, status, owner, blocked_by, notes FROM tasks WHERE project_name = ? ORDER BY task_key', (cmd['project'],)).fetchall()
            blockers = conn.execute('SELECT blocker_key, blocker_text, status FROM blockers WHERE project_name = ? ORDER BY blocker_key', (cmd['project'],)).fetchall()
            events = conn.execute('SELECT * FROM events WHERE project_name = ? ORDER BY rowid DESC LIMIT 10', (cmd['project'],)).fetchall()
            results.append({'op': op, 'project': dict(p) if p else None, 'tasks': [dict(r) for r in tasks], 'blockers': [dict(r) for r in blockers], 'events': [dict(r) for r in events]})
    elif op == 'mark_task_done':
        with connect() as conn:
            cur = conn.execute('UPDATE tasks SET status = ? WHERE project_name = ? AND task_key = ?', ('done', cmd['project'], cmd['task']))
            conn.commit()
            results.append({'op': op, 'rowcount': cur.rowcount})
    elif op == 'set_current_phase':
        with connect() as conn:
            cur = conn.execute('UPDATE projects SET current_phase = ? WHERE name = ?', (cmd['phase'], cmd['project']))
            conn.commit()
            results.append({'op': op, 'rowcount': cur.rowcount})
    elif op == 'add_event':
        with connect() as conn:
            conn.execute('INSERT INTO events (project_name, event_type, description, context) VALUES (?, ?, ?, ?)', (cmd['project'], cmd['event_type'], cmd['description'], cmd['context']))
            conn.commit()
            results.append({'op': op, 'status': 'ok'})
    elif op == 'list_tables':
        with connect() as conn:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            results.append({'op': op, 'tables': [r[0] for r in tables]})
    elif op == 'get_commits':
        with connect() as conn:
            rows = conn.execute("SELECT * FROM sqlite_master WHERE type='table'").fetchall()
            # Try common commit/feed table names
            for tname in ['commits', 'commit_feed', 'feed', 'activity', 'git_log']:
                try:
                    rows2 = conn.execute(f'SELECT * FROM {tname} WHERE project_name = ? ORDER BY rowid DESC LIMIT 10', (cmd['project'],)).fetchall()
                    results.append({'op': op, 'table': tname, 'rows': [dict(r) for r in rows2]})
                    break
                except Exception:
                    pass
            else:
                results.append({'op': op, 'table': None, 'rows': []})

print(json.dumps(results, indent=2))
