#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('db/state.db')
cursor = conn.cursor()

# List all projects
cursor.execute("SELECT name FROM projects")
projects = [row[0] for row in cursor.fetchall()]
print("Projects found:")
for project in projects:
    print(f"\n- {project}")
    # List tasks for this project
    cursor.execute("SELECT task_key, status FROM tasks WHERE project_name = ?", (project,))
    tasks = cursor.fetchall()
    if tasks:
        print("  Tasks:")
        for task_key, status in tasks:
            print(f"    - {task_key}: {status}")
    else:
        print("  No tasks found")

conn.close()
