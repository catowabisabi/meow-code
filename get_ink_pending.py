import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

cur.execute('SELECT src_path FROM files WHERE status="pending" AND src_path LIKE "src\\ink%" ORDER BY src_path LIMIT 50')
pending = [r[0] for r in cur.fetchall()]

print(f"Ink pending files ({len(pending)}):")
for f in pending:
    print(f"  {f}")