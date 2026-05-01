import sqlite3

conn = sqlite3.connect('/root/.openclaw/workspace/db/state.db')
cursor = conn.cursor()

# Step 1: Mark auth-flow task as done
cursor.execute("UPDATE tasks SET status = 'done' WHERE project_name = 'creator-suite' AND task_key = 'auth-flow'")
print(f"auth-flow updated: {cursor.rowcount} row(s)")

conn.commit()
conn.close()
