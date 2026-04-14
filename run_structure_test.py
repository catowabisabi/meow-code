import sqlite3
import os
import ast
import inspect

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

conn.commit()

tools_py = [f for f in os.listdir(tools_dir) if f.endswith('.py') and not f.startswith('_')]
print(f'Found {len(tools_py)} Python modules')

results = {'valid': 0, 'classes': 0, 'functions': 0, 'async_functions': 0}

for module_file in tools_py:
    module_name = module_file[:-3]
    module_path = os.path.join(tools_dir, module_file)
    
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef)]
        async_functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]
        
        c.execute('''INSERT INTO test_results 
                    (module_name, test_type, status, message) 
                    VALUES (?, ?, ?, ?)''',
                 (module_name, 'structure_check', 'PASSED', 
                  f'Classes: {len(classes)}, Functions: {len(functions)}, Async: {len(async_functions)}'))
        
        results['valid'] += 1
        results['classes'] += len(classes)
        results['functions'] += len(functions)
        results['async_functions'] += len(async_functions)
        
    except SyntaxError as e:
        c.execute('''INSERT INTO test_results 
                    (module_name, test_type, status, message, error_details) 
                    VALUES (?, ?, ?, ?, ?)''',
                 (module_name, 'structure_check', 'SYNTAX_ERROR', str(e)[:200], f'Line {e.lineno}'))
    except Exception as e:
        c.execute('''INSERT INTO test_results 
                    (module_name, test_type, status, message) 
                    VALUES (?, ?, ?, ?)''',
                 (module_name, 'structure_check', 'ERROR', str(e)[:200]))
    
    conn.commit()

print(f'\n=== Structure Check Results ===')
print(f'Valid modules: {results["valid"]}')
print(f'Total classes defined: {results["classes"]}')
print(f'Total functions defined: {results["functions"]}')
print(f'Total async functions defined: {results["async_functions"]}')

c.execute("SELECT module_name, message FROM test_results WHERE test_type = 'structure_check' AND status = 'PASSED' ORDER BY module_name")
passed = c.fetchall()
print(f'\n=== Passed Modules ({len(passed)}) ===')
for row in passed:
    print(f'{row[0]}: {row[1]}')

conn.commit()
conn.close()
print(f'\nResults recorded in: {db_path}')