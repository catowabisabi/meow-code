import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

cur.execute("SELECT src_path FROM files WHERE src_path LIKE '%hooks%' LIMIT 50")
print('Paths with hooks:')
for row in cur.fetchall():
    print(f'  {row[0]}')

conn.close()