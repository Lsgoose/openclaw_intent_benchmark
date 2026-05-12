import sqlite3

conn = sqlite3.connect('/root/.openclaw/workspace/db/state.db')
cursor = conn.cursor()

# Step 2: Update current_phase to dashboard-integration
cursor.execute("UPDATE projects SET current_phase = 'dashboard-integration', last_update = '2026-04-29 12:46:00' WHERE name = 'creator-suite'")
print(f"current_phase updated: {cursor.rowcount} row(s)")

conn.commit()
conn.close()
