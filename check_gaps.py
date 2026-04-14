#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute('SELECT status, COUNT(*) FROM files GROUP BY status')
print('=== Status Distribution ===')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')

c.execute('''
    SELECT src_path, notes FROM files 
    WHERE notes LIKE '%CRITICAL%' OR notes LIKE '%HIGH%' 
    LIMIT 10
''')
print('\n=== Recent Gap Findings ===')
for row in c.fetchall():
    print(f'  {row[0]}')
    if row[1]:
        print(f'    {row[1][:100]}...')
conn.close()
