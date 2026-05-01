#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('db/state.db')
conn.row_factory = sqlite3.Row
print('TASKS')
for row in conn.execute("select project_name, task_key, status from tasks where task_key='auth-flow'"):
    print(dict(row))
print('PROJECTS')
for row in conn.execute("select name, current_phase from projects"):
    print(dict(row))
