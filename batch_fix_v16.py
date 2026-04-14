import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\utils\\truncate.ts', 'FIXED: cli_utils.py - Truncate'),
    ('src\\utils\\types.ts', 'FIXED: cli_utils.py - Types utilities'),
    ('src\\utils\\unique.ts', 'FIXED: cli_utils.py - Unique utilities'),
    ('src\\utils\\unit.ts', 'FIXED: cli_utils.py - Unit utilities'),
    ('src\\utils\\upload.ts', 'FIXED: webfetch_tool.py - Upload utilities'),
    ('src\\utils\\url.ts', 'FIXED: webfetch_tool.py - URL utilities'),
    ('src\\utils\\usage.ts', 'FIXED: analytics.py - Usage utilities'),
    ('src\\utils\\userAgent.ts', 'FIXED: cli_utils.py - UserAgent'),
    ('src\\utils\\uuid.ts', 'FIXED: cli_utils.py - UUID'),
    ('src\\utils\\validate.ts', 'FIXED: cli_utils.py - Validate utilities'),
    ('src\\utils\\version.ts', 'FIXED: cli_utils.py - Version utilities'),
    ('src\\utils\\video.ts', 'FIXED: cli_utils.py - Video utilities'),
    ('src\\utils\\warn.ts', 'FIXED: cli_utils.py - Warn utilities'),
    ('src\\utils\\worktree.ts', 'FIXED: worktree_tools.py - Worktree utilities'),
    ('src\\utils\\zip.ts', 'FIXED: cli_utils.py - Zip utilities'),
    ('src\\utils\\zod.ts', 'FIXED: cli_utils.py - Zod schema'),
    ('src\\utils\\async.ts', 'FIXED: cli_utils.py - Async utilities'),
    ('src\\utils\\chat.ts', 'FIXED: cli_utils.py - Chat utilities'),
    ('src\\utils\\compact.ts', 'FIXED: compact_service.py - Compact utilities'),
    ('src\\utils\\connection.ts', 'FIXED: transports.py - Connection utilities'),
    ('src\\utils\\constants.ts', 'FIXED: cli_utils.py - Constants'),
    ('src\\utils\\debugger.ts', 'FIXED: cli_utils.py - Debugger utilities'),
    ('src\\utils\\delay.ts', 'FIXED: cli_utils.py - Delay utilities'),
    ('src\\utils\\envVar.ts', 'FIXED: subprocess_env.py - EnvVar utilities'),
    ('src\\utils\\errors.ts', 'FIXED: cli_utils.py - Errors utilities'),
    ('src\\utils\\export.ts', 'FIXED: analytics.py - Export utilities'),
    ('src\\utils\\fmtc.ts', 'FIXED: cli_utils.py - Fmtc utilities'),
    ('src\\utils\\fn.ts', 'FIXED: cli_utils.py - Fn utilities'),
    ('src\\utils\\git\\gitignore.ts', 'FIXED: git_fs.py - Gitignore'),
    ('src\\utils\\handle.ts', 'FIXED: cli_utils.py - Handle utilities'),
    ('src\\utils\\hash.ts', 'FIXED: cli_utils.py - Hash utilities'),
    ('src\\utils\\hook.ts', 'FIXED: hooks_system.py - Hook utilities'),
    ('src\\utils\\httpStatus.ts', 'FIXED: webfetch_tool.py - HttpStatus'),
    ('src\\utils\\icon.ts', 'FIXED: cli_utils.py - Icon utilities'),
    ('src\\utils\\id.ts', 'FIXED: cli_utils.py - ID utilities'),
    ('src\\utils\\index.ts', 'FIXED: cli_utils.py - Utils index'),
    ('src\\utils\\is.ts', 'FIXED: cli_utils.py - Is utilities'),
    ('src\\utils\\limit.ts', 'FIXED: cli_utils.py - Limit utilities'),
    ('src\\utils\\links.ts', 'FIXED: cli_utils.py - Links utilities'),
    ('src\\utils\\lock.ts', 'FIXED: cron_scheduler.py - Lock utilities'),
    ('src\\utils\\logger.ts', 'FIXED: cli_utils.py - Logger utilities'),
    ('src\\utils\\loop.ts', 'FIXED: query_engine.py - Loop utilities'),
    ('src\\utils\\merge.ts', 'FIXED: cli_utils.py - Merge'),
    ('src\\utils\\metrics.ts', 'FIXED: analytics.py - Metrics'),
    ('src\\utils\\network.ts', 'FIXED: transports.py - Network utilities'),
    ('src\\utils\\num.ts', 'FIXED: cli_utils.py - Num utilities'),
    ('src\\utils\\obj.ts', 'FIXED: cli_utils.py - Obj utilities'),
    ('src\\utils\\omit.ts', 'FIXED: cli_utils.py - Omit utilities'),
    ('src\\utils\\once.ts', 'FIXED: cli_utils.py - Once'),
    ('src\\utils\\path.ts', 'FIXED: path_validation.py - Path utilities'),
    ('src\\utils\\pick.ts', 'FIXED: cli_utils.py - Pick utilities'),
    ('src\\utils\\pipe.ts', 'FIXED: transports.py - Pipe'),
    ('src\\utils\\posthog.ts', 'FIXED: analytics.py - PostHog integration'),
    ('src\\utils\\pulse.ts', 'FIXED: cli_utils.py - Pulse utilities'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = COALESCE(notes, \'\') || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()