import sqlite3
from datetime import datetime
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()
c.execute('''
    UPDATE files 
    SET notes = notes || ' | FIXED: Created enhanced_types.py with ValidationResult, PermissionResult, aliases, searchHint, validateInput, checkPermissions, isEnabled, isConcurrencySafe, isDestructive, isMcp, shouldDefer, maxResultSizeChars, interruptBehavior'
    WHERE src_path = 'src\\Tool.ts'
''')
conn.commit()
c.execute('SELECT src_path, notes FROM files WHERE src_path = ?', ('src\\Tool.ts',))
row = c.fetchone()
print(f'Updated: {row[0]}')
print(f'Notes: {row[1][:200]}...')
conn.close()
