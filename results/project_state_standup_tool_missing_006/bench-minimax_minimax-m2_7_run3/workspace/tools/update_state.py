import sqlite3

conn = sqlite3.connect('/root/.openclaw/workspace/db/state.db')
cur = conn.cursor()

# Step 1: Update auth-flow task to done
cur.execute("UPDATE tasks SET status = 'done' WHERE project_name = 'creator-suite' AND task_key = 'auth-flow'")

# Step 2: Change creator-suite current_phase to dashboard-integration
cur.execute("UPDATE projects SET current_phase = 'dashboard-integration' WHERE name = 'creator-suite'")

# Step 3: Add progress event for auth-flow completion
cur.execute("""
    INSERT INTO events (project_name, event_type, description, context)
    VALUES ('creator-suite', 'progress', 'Auth flow completed for creator-suite',
            'Dashboard integration remains blocked on API schema finalization')
""")

conn.commit()

# Verify
print("=== After update ===")
cur.execute("SELECT * FROM tasks WHERE project_name='creator-suite'")
for row in cur.fetchall():
    print(row)
print()
cur.execute("SELECT * FROM projects WHERE name='creator-suite'")
print(cur.fetchone())
print()
cur.execute("SELECT * FROM events WHERE project_name='creator-suite'")
for row in cur.fetchall():
    print(row)
