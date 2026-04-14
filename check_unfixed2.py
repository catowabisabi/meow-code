import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

print('=== Truly Unfixed Records ===')
c.execute("SELECT COUNT(*) FROM files WHERE notes NOT LIKE '%FIXED:%' AND notes NOT LIKE '%PARTIAL:%'")
print(f'Not FIXED or PARTIAL: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
print(f'Have FIXED: {c.fetchone()[0]}')

print('\n=== By Original Priority (records WITHOUT FIXED) ===')
c.execute("SELECT notes FROM files WHERE notes NOT LIKE '%FIXED:%' AND notes NOT LIKE '%PARTIAL:%' LIMIT 10")
for row in c.fetchall():
    print(f'  {row[0][:100]}...' if len(row[0]) > 100 else f'  {row[0]}')

conn.close()