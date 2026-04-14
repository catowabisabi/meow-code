import sqlite3
import os
from datetime import datetime

db_path = r'F:\codebase\cato-claude\test_records.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS test_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_modules INTEGER,
    total_tests INTEGER,
    passed INTEGER,
    warnings INTEGER,
    failed INTEGER,
    completed_at TEXT DEFAULT CURRENT_TIMESTAMP
)''')

c.execute("SELECT COUNT(DISTINCT module_name) FROM functionality_test")
total_modules = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM functionality_test")
total_tests = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM functionality_test WHERE status = 'PASSED'")
passed = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM functionality_test WHERE status = 'WARNING'")
warnings = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM functionality_test WHERE status = 'FAILED'")
failed = c.fetchone()[0]

c.execute('''INSERT INTO test_summary (total_modules, total_tests, passed, warnings, failed) 
            VALUES (?, ?, ?, ?, ?)''',
         (total_modules, total_tests, passed, warnings, failed))

conn.commit()

print('=== FINAL TEST SUMMARY ===')
print(f'Database: {db_path}')
print(f'Total modules tested: {total_modules}')
print(f'Total tests: {total_tests}')
print(f'Passed: {passed}')
print(f'Warnings: {warnings}')
print(f'Failed: {failed}')
print(f'Success rate: {100*passed/total_tests:.1f}%')

conn.close()