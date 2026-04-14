import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

cur.execute('SELECT src_path FROM files WHERE status="pending" ORDER BY src_path LIMIT 100')
pending = [r[0] for r in cur.fetchall()]

print(f"Next 100 pending files:")
for i, f in enumerate(pending):
    print(f"{i+1}. {f}")