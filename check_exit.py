import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

cur.execute('SELECT src_path, status, summary FROM files WHERE src_path LIKE "%exit%"')
for row in cur.fetchall():
    print(f"Path: {row[0]}")
    print(f"Status: {row[1]}")
    print(f"Summary: {row[2]}")
    print()