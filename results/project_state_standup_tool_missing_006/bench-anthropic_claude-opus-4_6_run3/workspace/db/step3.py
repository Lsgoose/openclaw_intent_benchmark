import sqlite3

conn = sqlite3.connect('/root/.openclaw/workspace/db/state.db')
cursor = conn.cursor()

# Step 3: Add one progress event
cursor.execute(
    "INSERT INTO events (project_name, event_type, description, context, timestamp) VALUES (?, ?, ?, ?, ?)",
    (
        'creator-suite',
        'progress',
        'Auth flow completed; moving to dashboard-integration phase',
        'Dashboard integration remains blocked on API schema finalization',
        '2026-04-29 12:46:00'
    )
)
print(f"Event inserted: {cursor.rowcount} row(s)")

conn.commit()
conn.close()
