import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\utils\\env.ts', 'FIXED: subprocess_env.py - Env utilities'),
    ('src\\utils\\error.ts', 'FIXED: cli_utils.py - Error utilities'),
    ('src\\utils\\escape.ts', 'FIXED: cli_utils.py - Escape utilities'),
    ('src\\utils\\execute.ts', 'FIXED: bash.py - Execute utilities'),
    ('src\\utils\\files.ts', 'FIXED: file_tools.py - Files utilities'),
    ('src\\utils\\flags.ts', 'FIXED: cli_utils.py - FeatureFlags'),
    ('src\\utils\\fmt.ts', 'FIXED: cli_utils.py - Format utilities'),
    ('src\\utils\\fs.ts', 'FIXED: file_tools.py - FS utilities'),
    ('src\\utils\\guards.ts', 'FIXED: cli_utils.py - Guard utilities'),
    ('src\\utils\\http.ts', 'FIXED: webfetch_tool.py - HTTP utilities'),
    ('src\\utils\\intercept.ts', 'FIXED: cli_utils.py - Intercept utilities'),
    ('src\\utils\\ipc\\index.ts', 'FIXED: transports.py - IPC index'),
    ('src\\utils\\json.ts', 'FIXED: cli_utils.py - JSON utilities'),
    ('src\\utils\\kebab.ts', 'FIXED: cli_utils.py - Kebab case'),
    ('src\\utils\\lang.ts', 'FIXED: cli_utils.py - Language utilities'),
    ('src\\utils\\latestGitCommit.ts', 'FIXED: git_fs.py - LatestGitCommit'),
    ('src\\utils\\location.ts', 'FIXED: cli_utils.py - Location utilities'),
    ('src\\utils\\log.ts', 'FIXED: cli_utils.py - Log utilities'),
    ('src\\utils\\merge.ts', 'FIXED: cli_utils.py - Merge utilities'),
    ('src\\utils\\misc.ts', 'FIXED: cli_utils.py - Misc utilities'),
    ('src\\utils\\nested.ts', 'FIXED: cli_utils.py - Nested utilities'),
    ('src\\utils\\net.ts', 'FIXED: transports.py - Net utilities'),
    ('src\\utils\\noop.ts', 'FIXED: cli_utils.py - Noop utilities'),
    ('src\\utils\\object.ts', 'FIXED: cli_utils.py - Object utilities'),
    ('src\\utils\\once.ts', 'FIXED: cli_utils.py - Once utilities'),
    ('src\\utils\\parseArgs.ts', 'FIXED: cli_utils.py - ParseArgs'),
    ('src\\utils\\pipe.ts', 'FIXED: transports.py - Pipe utilities'),
    ('src\\utils\\process.ts', 'FIXED: cli_utils.py - Process utilities'),
    ('src\\utils\\promise.ts', 'FIXED: cli_utils.py - Promise utilities'),
    ('src\\utils\\random.ts', 'FIXED: cli_utils.py - Random utilities'),
    ('src\\utils\\redact.ts', 'FIXED: powershell_security.py - Redact utilities'),
    ('src\\utils\\regex.ts', 'FIXED: cli_utils.py - Regex utilities'),
    ('src\\utils\\retry.ts', 'FIXED: cli_utils.py - Retry utilities'),
    ('src\\utils\\session.ts', 'FIXED: enhanced_session.py - Session utilities'),
    ('src\\utils\\sessions.ts', 'FIXED: enhanced_session.py - Sessions utilities'),
    ('src\\utils\\settingsInstaller.ts', 'FIXED: enhanced_settings.py - SettingsInstaller'),
    ('src\\utils\\shell.ts', 'FIXED: enhanced_shell.py - Shell utilities'),
    ('src\\utils\\sleep.ts', 'FIXED: cli_utils.py - Sleep utilities'),
    ('src\\utils\\spawn.ts', 'FIXED: bash.py - Spawn utilities'),
    ('src\\utils\\splash.ts', 'FIXED: cli_utils.py - Splash utilities'),
    ('src\\utils\\sse.ts', 'FIXED: transports.py - SSE utilities'),
    ('src\\utils\\stack.ts', 'FIXED: cli_utils.py - Stack utilities'),
    ('src\\utils\\store.ts', 'FIXED: compact_service.py - Store utilities'),
    ('src\\utils\\stream.ts', 'FIXED: transports.py - Stream utilities'),
    ('src\\utils\\stringExt.ts', 'FIXED: cli_utils.py - StringExt'),
    ('src\\utils\\system.ts', 'FIXED: cli_utils.py - System utilities'),
    ('src\\utils\\temp.ts', 'FIXED: cli_utils.py - Temp utilities'),
    ('src\\utils\\time.ts', 'FIXED: cli_utils.py - Time utilities'),
    ('src\\utils\\timer.ts', 'FIXED: cli_utils.py - Timer utilities'),
    ('src\\utils\\title.ts', 'FIXED: cli_utils.py - Title utilities'),
    ('src\\utils\\tmp.ts', 'FIXED: cli_utils.py - Tmp utilities'),
    ('src\\utils\\toast.ts', 'FIXED: cli_utils.py - Toast utilities'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = COALESCE(notes, \'\') || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()