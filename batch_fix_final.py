import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\bridge\\jwtUtils.ts', 'FIXED: jwt_utils.py - JWTRefreshScheduler, decode_jwt_payload, scheduleFromExpiresIn'),
    ('src\\utils\\git\\gitFilesystem.ts', 'FIXED: git_fs.py - GitFilesystemReader'),
    ('src\\utils\\sessionRestore.ts', 'FIXED: git_fs.py - SessionRestore with worktree attribution'),
    ('src\\entrypoints\\agentSdkTypes.ts', 'FIXED: agent_sdk_types.py - ForkSession, tagSession, renameSession, CronTask, RemoteControlHandle'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()
