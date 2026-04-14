import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path, notes FROM files WHERE notes NOT LIKE '%FIXED%' AND notes NOT LIKE '%PARTIAL%' AND notes NOT LIKE '%NO_MATCH%' LIMIT 100")
rows = c.fetchall()
print(f'Remaining unfixed (not FIXED/PARTIAL/NO_MATCH): {len(rows)}')
for row in rows:
    print(f'  {row[0]}')
    if row[1]:
        print(f'    {row[1][:100]}')

conn.close()