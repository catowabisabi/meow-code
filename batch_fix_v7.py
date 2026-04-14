import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\utils\\plugins\\pluginLoader.ts', 'FIXED: plugin_system.py - PluginLoader with validation'),
    ('src\\utils\\plugins\\dependencyResolver.ts', 'FIXED: plugin_system.py - DependencyResolver'),
    ('src\\utils\\plugins\\marketplaceManager.ts', 'FIXED: plugin_system.py - MarketplaceManager'),
    ('src\\utils\\plugins\\loadPluginHooks.ts', 'FIXED: plugin_system.py - Hook registration'),
    ('src\\cli\\transports\\SerialBatchEventUploader.ts', 'PARTIAL: Batch upload - needs async queue'),
    ('src\\cli\\transports\\WorkerStateUploader.ts', 'PARTIAL: Worker state - needs async queue'),
    ('src\\cli\\update.ts', 'PARTIAL: Self-update - requires platform-specific implementation'),
    ('src\\commands\\advisor.ts', 'PARTIAL: Advisor - needs rule engine'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()
