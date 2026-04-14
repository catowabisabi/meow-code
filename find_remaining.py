import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path FROM files WHERE notes NOT LIKE '%FIXED%' AND notes IS NOT NULL AND notes NOT LIKE '%PARTIAL%' LIMIT 80")
rows = c.fetchall()
print(f'Unfixed gaps (not FIXED or PARTIAL): {len(rows)}')
for row in rows[:50]:
    print(f'  {row[0]}')

conn.close()