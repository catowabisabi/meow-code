import sqlite3
import sys
import os
import py_compile
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

c.execute('''CREATE TABLE IF NOT EXISTS syntax_check (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_name TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    error_line INTEGER,
    error_offset INTEGER,
    tested_at TEXT DEFAULT CURRENT_TIMESTAMP
)''')

conn.commit()

tools_py = [f for f in os.listdir(tools_dir) if f.endswith('.py') and not f.startswith('_')]
print(f'Found {len(tools_py)} Python modules')

syntax_results = {'valid': 0, 'syntax_error': 0, 'compile_error': 0}

for module_file in tools_py:
    module_name = module_file[:-3]
    module_path = os.path.join(tools_dir, module_file)
    
    try:
        py_compile.compile(module_path, doraise=True)
        c.execute('''INSERT INTO syntax_check (module_name, status, message) VALUES (?, ?, ?)''',
                 (module_name, 'VALID', 'Syntax is valid'))
        syntax_results['valid'] += 1
    except py_compile.PyCompileError as e:
        error_msg = str(e)
        line_no = None
        offset = None
        if 'line' in error_msg.lower():
            try:
                parts = error_msg.split('line')
                if len(parts) > 1:
                    line_no = int(parts[1].split()[0])
            except:
                pass
        c.execute('''INSERT INTO syntax_check (module_name, status, message, error_line) VALUES (?, ?, ?, ?)''',
                 (module_name, 'SYNTAX_ERROR', error_msg[:500], line_no))
        syntax_results['syntax_error'] += 1
    except Exception as e:
        c.execute('''INSERT INTO syntax_check (module_name, status, message) VALUES (?, ?, ?)''',
                 (module_name, 'ERROR', str(e)[:500]))
        syntax_results['compile_error'] += 1
    
    conn.commit()

print(f'\n=== Syntax Check Results ===')
print(f'Valid syntax: {syntax_results["valid"]}')
print(f'Syntax errors: {syntax_results["syntax_error"]}')
print(f'Compile errors: {syntax_results["compile_error"]}')

c.execute("SELECT module_name, message, error_line FROM syntax_check WHERE status = 'SYNTAX_ERROR' ORDER BY module_name LIMIT 20")
syntax_errors = c.fetchall()
if syntax_errors:
    print(f'\n=== Syntax Errors (first 20) ===')
    for row in syntax_errors:
        print(f'{row[0]}: line {row[2]}')
        print(f'  {row[1][:200]}')

conn.commit()
conn.close()
print(f'\nResults recorded in: {db_path}')