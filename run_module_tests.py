import sqlite3
import sys
import os
import importlib
import importlib.util
import traceback

db_path = r'F:\codebase\cato-claude\test_records.db'
tools_dir = r'F:\codebase\cato-claude\api_server\tools'

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

c.execute('''CREATE TABLE IF NOT EXISTS summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_modules INTEGER,
    passed INTEGER,
    failed INTEGER,
    errors INTEGER,
    completed_at TEXT DEFAULT CURRENT_TIMESTAMP
)''')

conn.commit()

print(f'Database created: {db_path}')

tools_py = [f for f in os.listdir(tools_dir) if f.endswith('.py') and not f.startswith('_')]
print(f'Found {len(tools_py)} Python modules in {tools_dir}')

results = {'passed': 0, 'failed': 0, 'errors': 0}

for module_file in tools_py:
    module_name = module_file[:-3]
    module_path = os.path.join(tools_dir, module_file)
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        has_functions = len([x for x in dir(module) if not x.startswith('_')]) > 0
        
        if has_functions:
            c.execute('''INSERT INTO test_results 
                        (module_name, test_type, status, message) 
                        VALUES (?, ?, ?, ?)''',
                     (module_name, 'import_test', 'PASSED', f'Successfully imported, found {len([x for x in dir(module) if not x.startswith("_")])} public members'))
            results['passed'] += 1
        else:
            c.execute('''INSERT INTO test_results 
                        (module_name, test_type, status, message) 
                        VALUES (?, ?, ?, ?)''',
                     (module_name, 'import_test', 'FAILED', 'Module imported but no public members found'))
            results['failed'] += 1
            
    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        c.execute('''INSERT INTO test_results 
                    (module_name, test_type, status, message, error_details) 
                    VALUES (?, ?, ?, ?, ?)''',
                 (module_name, 'import_test', 'ERROR', error_msg[:200], tb[-1000:]))
        results['errors'] += 1
    
    conn.commit()

c.execute('''INSERT INTO summary (total_modules, passed, failed, errors) VALUES (?, ?, ?, ?)''',
         (len(tools_py), results['passed'], results['failed'], results['errors']))
conn.commit()

print(f'\n=== Test Summary ===')
print(f'Total modules: {len(tools_py)}')
print(f'Passed: {results["passed"]}')
print(f'Failed: {results["failed"]}')
print(f'Errors: {results["errors"]}')

conn.close()
print(f'\nResults recorded in: {db_path}')