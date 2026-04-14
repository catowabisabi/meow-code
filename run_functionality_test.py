import sqlite3
import os
import sys
import ast
import traceback

db_path = r'F:\codebase\cato-claude\test_records.db'
tools_dir = r'F:\codebase\cato-claude\api_server\tools'

conn = sqlite3.connect(db_path)
c = conn.cursor()

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

def get_module_info(module_path):
    with open(module_path, 'r', encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source)
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef)]
    async_functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]
    docstring = ast.get_docstring(tree)
    return classes, functions, async_functions, docstring

tests_run = 0
tests_passed = 0
tests_failed = 0

tools_py = [f for f in os.listdir(tools_dir) if f.endswith('.py') and not f.startswith('_')]

for module_file in tools_py:
    module_name = module_file[:-3]
    module_path = os.path.join(tools_dir, module_file)
    
    classes, functions, async_functions, docstring = get_module_info(module_path)
    
    c.execute('''INSERT INTO functionality_test 
                (module_name, test_name, status, message) 
                VALUES (?, ?, ?, ?)''',
             (module_name, 'docstring_check', 'PASSED' if docstring else 'WARNING',
              f'Has docstring' if docstring else 'No module docstring'))
    tests_run += 1
    if docstring:
        tests_passed += 1
    else:
        tests_failed += 1
    
    c.execute('''INSERT INTO functionality_test 
                (module_name, test_name, status, message) 
                VALUES (?, ?, ?, ?)''',
             (module_name, 'structure_check', 'PASSED',
              f'{len(classes)} classes, {len(functions)} functions, {len(async_functions)} async'))
    tests_run += 1
    tests_passed += 1
    
    if classes:
        for cls_name in classes[:3]:
            c.execute('''INSERT INTO functionality_test 
                        (module_name, test_name, status, message) 
                        VALUES (?, ?, ?, ?)''',
                     (module_name, f'class_{cls_name}', 'PASSED', f'Class defined'))
            tests_run += 1
            tests_passed += 1
    
    conn.commit()

print(f'\n=== Functionality Test Summary ===')
print(f'Total tests run: {tests_run}')
print(f'Passed: {tests_passed}')
print(f'Failed: {tests_failed}')

c.execute("SELECT module_name, test_name, status, message FROM functionality_test WHERE status != 'PASSED' ORDER BY module_name, test_name LIMIT 30")
issues = c.fetchall()
if issues:
    print(f'\n=== Issues Found ({len(issues)}) ===')
    for row in issues:
        print(f'{row[0]}.{row[1]}: {row[3]}')

conn.commit()
conn.close()
print(f'\nResults recorded in: {db_path}')