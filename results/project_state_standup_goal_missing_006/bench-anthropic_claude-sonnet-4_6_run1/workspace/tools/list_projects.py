#!/usr/bin/env python3
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / 'db' / 'state.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=== PROJECTS ===")
for row in conn.execute('SELECT name, status, current_phase FROM projects').fetchall():
    print(dict(row))

print("\n=== TASKS ===")
for row in conn.execute('SELECT project_name, task_key, status FROM tasks ORDER BY project_name, task_key').fetchall():
    print(dict(row))
