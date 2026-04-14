import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path, notes FROM files WHERE notes IS NULL OR notes = '' LIMIT 30")
print('Records with no notes:')
for i, row in enumerate(c.fetchall(), 1):
    print(f'{i}. {row[0]}')

conn.close()