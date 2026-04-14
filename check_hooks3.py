import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM files WHERE src_path LIKE 'src\\\\hooks\\\\%'")
print('Total hooks files:', c.fetchall()[0])

c.execute("SELECT src_path FROM files WHERE src_path LIKE 'src\\\\hooks\\\\%' LIMIT 50")
print('Hooks files:')
for row in c.fetchall():
    print(f'  {row[0]}')

conn.close()