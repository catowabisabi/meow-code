import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM files WHERE status="analyzed"')
analyzed = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM files')
total = cur.fetchone()[0]

cur.execute('SELECT src_path FROM files WHERE status="pending" LIMIT 10')
pending = [r[0] for r in cur.fetchall()]

print(f"Analyzed: {analyzed}")
print(f"Total: {total}")
print(f"Pending: {total - analyzed}")
print(f"Progress: {analyzed/total*100:.1f}%")
print(f"\nPending samples (first 10):")
for p in pending:
    print(f"  {p}")