import sqlite3

conn = sqlite3.connect('/root/.openclaw/workspace/db/state.db')
cur = conn.cursor()

# Show schema for all tables
for table in ['projects', 'tasks', 'events', 'blockers']:
    print(f"\n=== {table} ===")
    cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
    print(cur.fetchone()[0])
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    print(f"Rows ({len(rows)}):")
    for row in rows:
        print(f"  {row}")
