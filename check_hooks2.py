import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path FROM files WHERE src_path LIKE '%useAbortableAsync%'")
print('useAbortableAsync:', c.fetchall())

c.execute("SELECT src_path FROM files WHERE src_path LIKE '%index.ts' AND src_path LIKE '%hooks%' LIMIT 10")
print('hooks index samples:', c.fetchall())

c.execute("SELECT src_path FROM files WHERE src_path = 'src\\\\hooks\\\\index.ts'")
print('Exact hooks index:', c.fetchall())

conn.close()