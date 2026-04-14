import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

test_path = r'src\hooks\useBlink.ts'
cur.execute('SELECT src_path FROM files WHERE src_path = ?', (test_path,))
print('Looking for:', repr(test_path))
print('Found:', cur.fetchall())

cur.execute('SELECT src_path FROM files LIMIT 1')
row = cur.fetchone()
print('First path repr:', repr(row[0]))
print('First path raw:', row[0])

conn.close()