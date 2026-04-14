import sqlite3
import os

db_path = r'F:\codebase\cato-claude\test_records.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print('=== Final Test Results Summary ===')

c.execute("SELECT COUNT(DISTINCT module_name) FROM functionality_test")
print(f'Total modules tested: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM functionality_test WHERE status = 'PASSED'")
print(f'Total tests passed: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM functionality_test WHERE status = 'WARNING'")
print(f'Total warnings: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM functionality_test WHERE status = 'FAILED'")
print(f'Total failures: {c.fetchone()[0]}')

print('\n=== Tests by Category ===')
c.execute("SELECT test_name, COUNT(*) FROM functionality_test GROUP BY test_name")
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')

print('\n=== Module Test Counts (top 10) ===')
c.execute("SELECT module_name, COUNT(*) as cnt FROM functionality_test GROUP BY module_name ORDER BY cnt DESC LIMIT 10")
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]} tests')

conn.close()
print(f'\nFull results in: {db_path}')