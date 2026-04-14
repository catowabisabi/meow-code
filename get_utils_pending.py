import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

cur.execute('SELECT src_path FROM files WHERE status="pending" AND src_path LIKE "src\\\\utils\\\\%" ORDER BY src_path LIMIT 60')
pending = [r[0] for r in cur.fetchall()]

print(f"Pending utils files ({len(pending)}):")
for f in pending:
    print(f"  {repr(f)}")