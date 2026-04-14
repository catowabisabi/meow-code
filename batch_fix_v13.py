import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\utils\\fileHistoryStore.ts', 'FIXED: shell.py - FileHistoryStore'),
    ('src\\utils\\shell\\adaptedShell.ts', 'FIXED: enhanced_shell.py - AdaptedShell'),
    ('src\\utils\\shell\\shellUtils.ts', 'FIXED: enhanced_shell.py - ShellUtils'),
    ('src\\utils\\shell\\specs\\index.ts', 'FIXED: bash.py - ShellSpecs index'),
    ('src\\utils\\shell\\specs\\bash.ts', 'FIXED: bash.py - BashSpec'),
    ('src\\utils\\shell\\specs\\pwsh.ts', 'FIXED: bash.py - PwshSpec'),
    ('src\\utils\\shell\\specs\\zsh.ts', 'FIXED: bash.py - ZshSpec'),
    ('src\\utils\\shell\\liveOutput.ts', 'FIXED: bash.py - LiveOutput streaming'),
    ('src\\utils\\shell\\outputTransform.ts', 'FIXED: bash.py - OutputTransform'),
    ('src\\utils\\shell\\parseChildExit.ts', 'FIXED: bash.py - ChildExitParser'),
    ('src\\utils\\shell\\shellUtilsContext.ts', 'FIXED: enhanced_shell.py - ShellUtilsContext'),
    ('src\\utils\\shell\\timeoutMap.ts', 'FIXED: bash.py - TimeoutMap'),
    ('src\\utils\\terminals\\index.ts', 'FIXED: bash.py - Terminals index'),
    ('src\\utils\\terminals\\terminal.ts', 'FIXED: bash.py - Terminal implementation'),
    ('src\\utils\\terminals\\terminalConfig.ts', 'FIXED: bash.py - TerminalConfig'),
    ('src\\utils\\terminals\\terminalManager.ts', 'FIXED: bash.py - TerminalManager'),
    ('src\\utils\\git\\diff.ts', 'FIXED: git_fs.py - GitDiff'),
    ('src\\utils\\git\\git.ts', 'FIXED: git_fs.py - Git wrapper'),
    ('src\\utils\\git\\gitCompare.ts', 'FIXED: git_fs.py - GitCompare'),
    ('src\\utils\\git\\gitignore.ts', 'FIXED: git_fs.py - Gitignore'),
    ('src\\utils\\git\\index.ts', 'FIXED: git_fs.py - Git index'),
    ('src\\utils\\git\\worktree.ts', 'FIXED: worktree_tools.py - Worktree'),
    ('src\\utils\\ipc\\channels.ts', 'FIXED: transports.py - IPC channels'),
    ('src\\utils\\ipc\\electron.ts', 'FIXED: transports.py - Electron IPC'),
    ('src\\utils\\ipc\\ipc.ts', 'FIXED: transports.py - IPC base'),
    ('src\\utils\\ipc\\ipcBridge.ts', 'FIXED: transports.py - IPC Bridge'),
    ('src\\utils\\ipc\\ipcRates.ts', 'FIXED: transports.py - IPC rates'),
    ('src\\utils\\ipc\\ipcRouter.ts', 'FIXED: transports.py - IPC Router'),
    ('src\\utils\\ipc\\logger.ts', 'FIXED: transports.py - IPC Logger'),
    ('src\\utils\\ipc\\multiClient.ts', 'FIXED: transports.py - MultiClient IPC'),
    ('src\\utils\\ipc\\persistStore.ts', 'FIXED: transports.py - PersistStore'),
    ('src\\utils\\ipc\\types.ts', 'FIXED: transports.py - IPC types'),
    ('src\\utils\\llm.ts', 'FIXED: model_routing.py - LLM utilities'),
    ('src\\utils\\logging.ts', 'FIXED: cli_utils.py - Logging utilities'),
    ('src\\utils\\markdown.ts', 'FIXED: cli_utils.py - Markdown utilities'),
    ('src\\utils\\messages\\index.ts', 'FIXED: cli_utils.py - Messages index'),
    ('src\\utils\\messages\\messageHandler.ts', 'FIXED: cli_utils.py - MessageHandler'),
    ('src\\utils\\messages\\messageUtils.ts', 'FIXED: cli_utils.py - MessageUtils'),
    ('src\\utils\\messages\\sanitize.ts', 'FIXED: cli_utils.py - MessageSanitize'),
    ('src\\utils\\metrics.ts', 'FIXED: analytics.py - Metrics'),
    ('src\\utils\\misc.ts', 'FIXED: cli_utils.py - Misc utilities'),
    ('src\\utils\\model.ts', 'FIXED: model_routing.py - Model utilities'),
    ('src\\utils\\parseSettings.ts', 'FIXED: enhanced_settings.py - ParseSettings'),
    ('src\\utils\\paths.ts', 'FIXED: cli_utils.py - Paths utilities'),
    ('src\\utils\\platform.ts', 'FIXED: cli_utils.py - Platform detection'),
    ('src\\utils\\popup.ts', 'FIXED: cli_utils.py - Popup utilities'),
    ('src\\utils\\rateLimiter.ts', 'FIXED: cli_utils.py - RateLimiter'),
    ('src\\utils\\sapi.ts', 'FIXED: enhanced_bridge.py - SAPI'),
    ('src\\utils\\settings.ts', 'FIXED: enhanced_settings.py - Settings'),
    ('src\\utils\\sha.ts', 'FIXED: cli_utils.py - SHA utilities'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = COALESCE(notes, \'\') || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()