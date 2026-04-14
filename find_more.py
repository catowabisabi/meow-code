import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path FROM files WHERE notes NOT LIKE '%FIXED%' AND notes IS NOT NULL LIMIT 100")
rows = c.fetchall()
print(f'Remaining unfixed with notes: {len(rows)}')
for row in rows[:50]:
    print(f'  {row[0]}')

conn.close()