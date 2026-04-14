import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM files WHERE status="pending"')
pending_count = cur.fetchone()[0]

cur.execute('SELECT src_path FROM files WHERE status="pending" ORDER BY src_path LIMIT 30')
pending = [r[0] for r in cur.fetchall()]

print(f"Total pending: {pending_count}")
print(f"\nFirst 30 pending files:")
for f in pending:
    print(f"  {repr(f)}")