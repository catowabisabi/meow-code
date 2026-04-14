import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\hooks\\useDiffInIDE.ts', 'FIXED: ide_proxy.py - IDEDiff'),
    ('src\\utils\\ide.ts', 'FIXED: ide_proxy.py - detect_ides, find_available_ide'),
    ('src\\upstreamproxy\\upstreamproxy.ts', 'FIXED: ide_proxy.py - UpstreamProxy'),
    ('src\\upstreamproxy\\relay.ts', 'PARTIAL: Binary relay - requires protobuf'),
    ('src\\remote\\sdkMessageAdapter.ts', 'PARTIAL: SDK message adapter - needs WebSocket'),
    ('src\\services\\api\\errorUtils.ts', 'FIXED: Enhanced error handling'),
    ('src\\services\\api\\promptCacheBreakDetection.ts', 'PARTIAL: Cache detection - needs monitoring'),
    ('src\\entrypoints\\sdk\\controlSchemas.ts', 'PARTIAL: SDK control protocol - needs schema'),
    ('src\\state\\AppState.tsx', 'PARTIAL: React UI - requires WebSocket push'),
    ('src\\state\\AppStateStore.ts', 'PARTIAL: Reactive store - requires async pub/sub'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()
