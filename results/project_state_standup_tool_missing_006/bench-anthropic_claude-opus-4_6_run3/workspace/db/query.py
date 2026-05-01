import sqlite3

conn = sqlite3.connect('/root/.openclaw/workspace/db/state.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", tables)

# For each table, show schema and all rows
for (table_name,) in tables:
    print(f"\n--- {table_name} ---")
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = cursor.fetchall()
    print("Columns:", cols)
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

conn.close()
