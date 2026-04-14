import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\hooks\\useRemoteSession.ts', 'FIXED: remote_swarm.py - RemoteSession'),
    ('src\\hooks\\useReplBridge.tsx', 'PARTIAL: REPL bridge - requires terminal IO'),
    ('src\\hooks\\useSwarmPermissionPoller.ts', 'FIXED: remote_swarm.py - SwarmCoordinator'),
    ('src\\utils\\swarm\\inProcessRunner.ts', 'FIXED: remote_swarm.py - SwarmCoordinator'),
    ('src\\utils\\swarm\\leaderPermissionBridge.ts', 'FIXED: remote_swarm.py - LeaderPermissionBridge'),
    ('src\\utils\\swarm\\permissionSync.ts', 'FIXED: remote_swarm.py - Permission sync'),
    ('src\\utils\\swarm\\spawnInProcess.ts', 'PARTIAL: In-process spawn - requires AsyncLocalStorage'),
    ('src\\bridge\\bridgeMain.ts', 'PARTIAL: Bridge daemon - requires subprocess management'),
    ('src\\bridge\\sessionRunner.ts', 'FIXED: transports.py - WebSocket transport'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()
