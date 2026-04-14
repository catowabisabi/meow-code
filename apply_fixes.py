import sqlite3
from datetime import datetime
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\Tool.ts', 'FIXED: Created enhanced_types.py with ValidationResult, PermissionResult, aliases, searchHint, validateInput, checkPermissions, isEnabled, isConcurrencySafe, isDestructive, isMcp, shouldDefer, maxResultSizeChars'),
    
    ('src\\utils\\Shell.ts', 'FIXED: Created enhanced_shell.py with CwdTracker, ShellProvider abstraction, bash/powershell support, CWD recovery'),
    
    ('src\\utils\\permissions\\permissions.ts', 'FIXED: Created enhanced_permissions.py with PermissionManager, path validation, shell rule matching, YoloClassifier'),
    
    ('src\\bridge\\bridgeApi.ts', 'FIXED: Created enhanced_bridge.py with BridgeApiClient, environment registration, work polling, heartbeat'),
    
    ('src\\utils\\settings\\settings.ts', 'FIXED: Created enhanced_settings.py with SettingsManager, SettingsSourcePriority, SettingsMerger, MDM support'),
    
    ('src\\utils\\sessionState.ts', 'FIXED: Created enhanced_session.py with SessionStateMachine (idle/running/requires_action), RequiresActionDetails'),
    
    ('src\\tools\\AgentTool\\AgentTool.tsx', 'FIXED: Created enhanced_agent.py with WorktreeManager, AgentLifecycle, AgentRegistry, MCP validation'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))
    print(f'Updated: {path}')

conn.commit()

# Verify
c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
count = c.fetchone()[0]
print(f'\nTotal FIXED records: {count}')

conn.close()
