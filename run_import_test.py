import sqlite3
import sys
import os
import traceback

db_path = r'F:\codebase\cato-claude\test_records.db'
tools_dir = r'F:\codebase\cato-claude\api_server\tools'

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

conn.commit()

sys.path.insert(0, tools_dir)

tools_py = [f for f in os.listdir(tools_dir) if f.endswith('.py') and not f.startswith('_')]
print(f'Found {len(tools_py)} Python modules')

results = {'passed': 0, 'failed': 0, 'error': 0}

for module_file in tools_py:
    module_name = module_file[:-3]
    
    try:
        module = __import__(module_name, fromlist=[''])
        members = [x for x in dir(module) if not x.startswith('_')]
        
        c.execute('''INSERT INTO import_test (module_name, status, public_members) VALUES (?, ?, ?)''',
                 (module_name, 'PASSED', ','.join(members[:20])))
        results['passed'] += 1
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)[:300]
        c.execute('''INSERT INTO import_test (module_name, status, error_type, error_message) VALUES (?, ?, ?, ?)''',
                 (module_name, 'FAILED', error_type, error_msg))
        results['error'] += 1
    
    conn.commit()

print(f'\n=== Import Test Results ===')
print(f'Passed: {results["passed"]}')
print(f'Failed: {results["error"]}')

c.execute("SELECT module_name, error_type, error_message FROM import_test WHERE status = 'FAILED' ORDER BY error_type, module_name")
failures = c.fetchall()
if failures:
    error_types = {}
    for row in failures:
        et = row[1]
        if et not in error_types:
            error_types[et] = []
        error_types[et].append(row[0])
    
    print(f'\n=== Errors by Type ===')
    for et, mods in error_types.items():
        print(f'\n{et} ({len(mods)} modules):')
        for m in mods[:5]:
            print(f'  - {m}')
        if len(mods) > 5:
            print(f'  ... and {len(mods) - 5} more')

conn.commit()
conn.close()
print(f'\nResults recorded in: {db_path}')