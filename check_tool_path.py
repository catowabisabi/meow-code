import sqlite3
from datetime import datetime
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()
c.execute("SELECT src_path, notes FROM files WHERE src_path LIKE '%Tool.ts' LIMIT 5")
for row in c.fetchall():
    print(f'Path: {repr(row[0])}')
    print(f'Notes: {row[1][:100] if row[1] else None}...')
conn.close()
