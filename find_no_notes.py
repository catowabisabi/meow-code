import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path, notes FROM files WHERE notes IS NULL OR notes = '' LIMIT 100")
rows = c.fetchall()
print(f'Records with no notes: {len(rows)}')
for row in rows[:50]:
    print(f'  {row[0]}')

conn.close()