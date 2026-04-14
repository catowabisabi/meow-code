import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\utils\\Shell.ts', 'FIXED: Created enhanced_shell.py with CwdTracker, ShellProvider abstraction, bash/powershell support'),
    ('src\\utils\\permissions\\permissions.ts', 'FIXED: Created enhanced_permissions.py with PermissionManager, path validation, shell rule matching, YoloClassifier'),
    ('src\\bridge\\bridgeApi.ts', 'FIXED: Created enhanced_bridge.py with BridgeApiClient, environment registration, work polling, heartbeat'),
]

for path, fix in fixes:
    c.execute('''
        UPDATE files 
        SET notes = notes || ' | ''' + fix + ''''
        WHERE src_path = ?
    ''', (path,))
    print(f'Updated: {path}')

conn.commit()
conn.close()
print('Database updated')
