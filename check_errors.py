import sqlite3
import os

db_path = r'F:\codebase\cato-claude\test_records.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("SELECT module_name, error_details FROM test_results WHERE status = 'ERROR' ORDER BY module_name LIMIT 20")
rows = c.fetchall()

print('First 20 errors:')
for row in rows:
    print(f'\n{row[0]}:')
    print(f'  {row[1][:500]}')

conn.close()