import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

print('=== Database Status ===')
c.execute('SELECT COUNT(*) FROM files')
print(f'Total records: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
print(f'FIXED: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%PARTIAL:%'")
print(f'PARTIAL: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%NO_MATCH:%'")
print(f'NO_MATCH: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM files WHERE notes IS NULL OR notes = ''")
print(f'No notes: {c.fetchone()[0]}')

print('\n=== Checking for CRITICAL/HIGH/MEDIUM/LOW markers ===')
c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%CRITICAL:%'")
print(f'CRITICAL markers: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%HIGH:%'")
print(f'HIGH markers: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%MEDIUM:%'")
print(f'MEDIUM markers: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%LOW:%'")
print(f'LOW markers: {c.fetchone()[0]}')

print('\n=== Sample FIXED records ===')
c.execute("SELECT src_path, notes FROM files WHERE notes LIKE '%FIXED:%' LIMIT 5")
for row in c.fetchall():
    print(f'{row[0]}: {row[1][:80]}...')

conn.close()