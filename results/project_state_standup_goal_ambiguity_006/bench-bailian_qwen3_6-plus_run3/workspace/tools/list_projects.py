#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('db/state.db')
rows = conn.execute('SELECT name, status, current_phase FROM projects').fetchall()
for r in rows:
    print(r)
