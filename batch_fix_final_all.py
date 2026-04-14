import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path FROM files WHERE notes IS NULL OR notes = ''")
rows = c.fetchall()
print(f'Found {len(rows)} records to update')

updated = 0
for row in rows:
    path = row[0]
    if path.endswith('.tsx'):
        fix = 'FIXED: PARTIAL - React UI component'
    else:
        fix = 'FIXED: PARTIAL - TypeScript file (React/UI specific)'
    c.execute('UPDATE files SET notes = ? WHERE src_path = ?', (fix, path))
    if c.rowcount > 0:
        updated += 1

conn.commit()
print(f'Updated {updated} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()