import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\QueryEngine.ts', 'FIXED: query_engine.py - QueryEngine, ToolExecutor, streaming, compact'),
    ('src\\cli\\transports\\SSETransport.ts', 'FIXED: transports.py - SSETransport'),
    ('src\\cli\\transports\\WebSocketTransport.ts', 'FIXED: transports.py - WebSocketTransport'),
    ('src\\cli\\transports\\HybridTransport.ts', 'FIXED: transports.py - HybridTransport'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

conn.close()
