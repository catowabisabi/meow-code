import sqlite3
from datetime import datetime

conn = sqlite3.connect('.hermes/autoloop/progress.db')
cur = conn.cursor()

# Mark todo 26 as completed (admin dept/team stubs fix)
cur.execute("SELECT id FROM todo WHERE title LIKE '%Admin dept/team stubs%'")
row = cur.fetchone()
if row:
    cur.execute("UPDATE todo SET status='completed', updated_at=? WHERE id=?", (datetime.now().isoformat(), row[0]))
    print(f"Todo #{row[0]} marked completed")
else:
    cur.execute(
        "INSERT INTO todo (title, detail, priority, status, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "Admin dept/team stubs → real CRUD",
            "admin/routes.py list_departments/create_department and list_teams/create_team were stubs (return [] / placeholder). Now delegate to DepartmentRepository and TeamRepository.",
            2, "completed", "code-quality", datetime.now().isoformat(), datetime.now().isoformat()
        )
    )
    print(f"New todo created")

conn.commit()
conn.close()