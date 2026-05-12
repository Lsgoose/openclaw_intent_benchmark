import sqlite3

conn = sqlite3.connect('/root/.openclaw/workspace/db/state.db')
cursor = conn.cursor()

# Verify creator-suite project
cursor.execute("SELECT name, current_phase, last_update FROM projects WHERE name = 'creator-suite'")
print("Project:", cursor.fetchone())

# Verify auth-flow task
cursor.execute("SELECT task_key, status FROM tasks WHERE project_name = 'creator-suite' AND task_key = 'auth-flow'")
print("Task:", cursor.fetchone())

# Verify latest event
cursor.execute("SELECT event_type, description, context, timestamp FROM events WHERE project_name = 'creator-suite' ORDER BY id DESC LIMIT 1")
print("Latest event:", cursor.fetchone())

conn.close()
