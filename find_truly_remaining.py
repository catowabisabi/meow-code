import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path FROM files WHERE notes NOT LIKE '%FIXED%' AND notes NOT LIKE '%PARTIAL%' AND notes NOT LIKE '%NO_MATCH%' AND notes IS NOT NULL AND notes != '' LIMIT 50")
rows = c.fetchall()
print(f'Remaining unfixed gaps with notes: {len(rows)}')
for row in rows:
    print(f'  {row[0]}')

conn.close()