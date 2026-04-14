import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path FROM files WHERE src_path LIKE '%command%' LIMIT 50")
rows = c.fetchall()
print(f'Files with command: {len(rows)}')
for row in rows[:30]:
    print(f'  {row[0]}')

conn.close()