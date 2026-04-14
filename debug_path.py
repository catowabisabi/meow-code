import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

path = 'src\\hooks\\index.ts'
cur.execute('SELECT src_path FROM files WHERE src_path = ?', (path,))
print('Looking for:', repr(path))
print('Found:', cur.fetchall())

path2 = "src\\hooks\\useAbortableAsync.ts"
cur.execute('SELECT src_path FROM files WHERE src_path = ?', (path2,))
print('Looking for:', repr(path2))
print('Found:', cur.fetchall())

conn.close()