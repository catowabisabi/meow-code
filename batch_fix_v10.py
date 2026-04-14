import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\ink\\termio\\dec.ts', 'FIXED: terminal_voice.py - DECMode'),
    ('src\\ink\\termio\\tokenize.ts', 'FIXED: terminal_voice.py - ANSITokenizer'),
    ('src\\hooks\\useVoice.ts', 'FIXED: terminal_voice.py - VoiceRecorder'),
    ('src\\hooks\\toolPermission\\PermissionContext.ts', 'PARTIAL: React IPC pattern - requires async context'),
    ('src\\hooks\\toolPermission\\handlers\\interactiveHandler.ts', 'PARTIAL: Interactive handler - requires terminal IO'),
    ('src\\components\\IdeAutoConnectDialog.tsx', 'PARTIAL: React UI - requires frontend'),
    ('src\\migrations\\migrateAutoUpdatesToSettings.ts', 'PARTIAL: Migration - uses different settings model'),
    ('src\\migrations\\migrateBypassPermissionsAcceptedToSettings.ts', 'PARTIAL: Permission migration - uses different security model'),
    ('src\\entrypoints\\init.ts', 'PARTIAL: Lifespan - needs telemetry/OAuth/proxy setup'),
    ('src\\commands\\insights.ts', 'PARTIAL: Insights - needs remote collection'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()
