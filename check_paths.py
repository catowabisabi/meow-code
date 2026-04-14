import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

cur.execute("SELECT src_path FROM files LIMIT 10")
print('Sample paths:')
for row in cur.fetchall():
    print(f'  {repr(row[0])}')

conn.close()