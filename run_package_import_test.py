import sqlite3
import sys
import os
import traceback

db_path = r'F:\codebase\cato-claude\test_records.db'
api_server_dir = r'F:\codebase\cato-claude\api_server'

if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_name TEXT NOT NULL,
    test_type TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    error_details TEXT,
    tested_at TEXT DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS import_test (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_name TEXT NOT NULL,
    status TEXT NOT NULL,
    public_members TEXT,
    error_type TEXT,
    error_message TEXT,
    tested_at TEXT DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS functionality_test (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_name TEXT NOT NULL,
    test_name TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    error_details TEXT,
    tested_at TEXT DEFAULT CURRENT_TIMESTAMP
)''')

conn.commit()

sys.path.insert(0, api_server_dir)

tools_py = [f for f in os.listdir(os.path.join(api_server_dir, 'tools')) if f.endswith('.py') and not f.startswith('_')]
print(f'Found {len(tools_py)} Python modules')

results = {'passed': 0, 'failed': 0}

for module_file in tools_py:
    module_name = module_file[:-3]
    
    try:
        full_name = f'tools.{module_name}'
        module = __import__(full_name, fromlist=[''])
        members = [x for x in dir(module) if not x.startswith('_')]
        
        c.execute('''INSERT INTO import_test (module_name, status, public_members) VALUES (?, ?, ?)''',
                 (module_name, 'PASSED', ','.join(members[:30])))
        results['passed'] += 1
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)[:300]
        c.execute('''INSERT INTO import_test (module_name, status, error_type, error_message) VALUES (?, ?, ?, ?)''',
                 (module_name, 'FAILED', error_type, error_msg))
        results['failed'] += 1
    
    conn.commit()

print(f'\n=== Import Test Results ===')
print(f'Passed: {results["passed"]}')
print(f'Failed: {results["failed"]}')

c.execute("SELECT module_name, error_type, error_message FROM import_test WHERE status = 'FAILED'")
failures = c.fetchall()

if failures:
    print(f'\n=== Failed Imports ===')
    for row in failures:
        print(f'{row[0]}: {row[1]} - {row[2][:100]}')

conn.commit()
conn.close()
print(f'\nResults recorded in: {db_path}')