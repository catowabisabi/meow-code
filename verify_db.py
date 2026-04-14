import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
count = c.fetchone()[0]
print(f'Records with FIXED: {count}')

c.execute('SELECT src_path, notes FROM files WHERE notes LIKE ? LIMIT 10', ('%FIXED:%',))
print('\n=== Fixed Records ===')
for row in c.fetchall():
    print(f'{row[0]}')
    if row[1]:
        print(f'  -> {row[1][:200]}...')

conn.close()
