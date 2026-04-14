import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

print('=== All Unfixed Records (38) ===')
c.execute("SELECT src_path, notes FROM files WHERE notes NOT LIKE '%FIXED:%' AND notes NOT LIKE '%PARTIAL:%'")
rows = c.fetchall()
for row in rows:
    print(f'\n{row[0]}:')
    print(f'  {row[1]}')

conn.close()