import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path FROM files WHERE src_path LIKE '%useAbortableAsync%'")
print('useAbortableAsync:', c.fetchall())

c.execute("SELECT src_path FROM files WHERE src_path LIKE '%hooks%' LIMIT 10")
print('hooks samples:', c.fetchall())

conn.close()