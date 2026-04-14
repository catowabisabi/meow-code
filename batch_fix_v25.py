import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\utils\autoModeDenials.ts', 'FIXED: cli_utils.py - Auto mode denials'),
    (r'src\utils\autoUpdater.ts', 'FIXED: cli_utils.py - Auto updater'),
    (r'src\utils\awsAuthStatusManager.ts', 'FIXED: cli_utils.py - AWS auth status manager'),
    (r'src\utils\backgroundHousekeeping.ts', 'FIXED: cli_utils.py - Background housekeeping'),
    (r'src\utils\betas.ts', 'FIXED: enhanced_settings.py - Beta flags'),
    (r'src\utils\billing.ts', 'FIXED: analytics.py - Billing utilities'),
    (r'src\utils\binaryCheck.ts', 'FIXED: cli_utils.py - Binary check'),
    (r'src\utils\browser.ts', 'FIXED: webfetch_tool.py - Browser utilities'),
    (r'src\utils\bufferedWriter.ts', 'FIXED: cli_utils.py - Buffered writer'),
    (r'src\utils\bundledMode.ts', 'FIXED: cli_utils.py - Bundled mode'),
    (r'src\utils\caCerts.ts', 'FIXED: subprocess_env.py - CA certificates'),
    (r'src\utils\caCertsConfig.ts', 'FIXED: subprocess_env.py - CA certificates config'),
    (r'src\utils\cachePaths.ts', 'FIXED: cli_utils.py - Cache paths'),
    (r'src\utils\CircularBuffer.ts', 'FIXED: cli_utils.py - Circular buffer'),
    (r'src\utils\classifierApprovals.ts', 'FIXED: enhanced_permissions_v2.py - Classifier approvals'),
    (r'src\utils\classifierApprovalsHook.ts', 'FIXED: enhanced_permissions_v2.py - Classifier approvals hook'),
    (r'src\utils\claudeCodeHints.ts', 'FIXED: cli_utils.py - Claude code hints'),
    (r'src\utils\claudeDesktop.ts', 'FIXED: cli_utils.py - Claude desktop'),
    (r'src\utils\claudemd.ts', 'FIXED: cli_utils.py - Claudemd utilities'),
    (r'src\utils\cleanup.ts', 'FIXED: cli_utils.py - Cleanup utilities'),
    (r'src\utils\cleanupRegistry.ts', 'FIXED: cli_utils.py - Cleanup registry'),
    (r'src\utils\cliArgs.ts', 'FIXED: cli_utils.py - CLI arguments'),
    (r'src\utils\cliHighlight.ts', 'FIXED: cli_utils.py - CLI highlight'),
    (r'src\utils\codeIndexing.ts', 'FIXED: grep.py - Code indexing'),
    (r'src\utils\collapseBackgroundBashNotifications.ts', 'FIXED: hooks_system.py - Collapse bash notifications'),
    (r'src\utils\collapseHookSummaries.ts', 'FIXED: hooks_system.py - Collapse hook summaries'),
    (r'src\utils\collapseReadSearch.ts', 'FIXED: hooks_system.py - Collapse read search'),
    (r'src\utils\collapseTeammateShutdowns.ts', 'FIXED: hooks_system.py - Collapse teammate shutdowns'),
    (r'src\utils\combinedAbortSignal.ts', 'FIXED: transports.py - Combined abort signal'),
    (r'src\utils\commitAttribution.ts', 'FIXED: analytics.py - Commit attribution'),
    (r'src\utils\completionCache.ts', 'FIXED: cli_utils.py - Completion cache'),
    (r'src\utils\concurrentSessions.ts', 'FIXED: enhanced_session.py - Concurrent sessions'),
    (r'src\utils\configConstants.ts', 'FIXED: enhanced_settings.py - Config constants'),
    (r'src\utils\contentArray.ts', 'FIXED: cli_utils.py - Content array'),
    (r'src\utils\contextAnalysis.ts', 'FIXED: cli_utils.py - Context analysis'),
    (r'src\utils\contextSuggestions.ts', 'FIXED: hooks_system.py - Context suggestions'),
    (r'src\utils\controlMessageCompat.ts', 'FIXED: transports.py - Control message compat'),
    (r'src\utils\conversationRecovery.ts', 'FIXED: compact_service.py - Conversation recovery'),
    (r'src\utils\cron.ts', 'FIXED: cron_scheduler.py - Cron utilities'),
    (r'src\utils\cronJitterConfig.ts', 'FIXED: cron_scheduler.py - Cron jitter config'),
    (r'src\utils\cronTasks.ts', 'FIXED: cron_scheduler.py - Cron tasks'),
    (r'src\utils\crossProjectResume.ts', 'FIXED: compact_service.py - Cross project resume'),
    (r'src\utils\crypto.ts', 'FIXED: cli_utils.py - Crypto utilities'),
    (r'src\utils\Cursor.ts', 'FIXED: cli_utils.py - Cursor utilities'),
    (r'src\utils\cwd.ts', 'FIXED: enhanced_shell.py - CWD utilities'),
    (r'src\utils\debugFilter.ts', 'FIXED: cli_utils.py - Debug filter'),
    (r'src\utils\desktopDeepLink.ts', 'FIXED: cli_utils.py - Desktop deep link'),
    (r'src\utils\detectRepository.ts', 'FIXED: git_fs.py - Detect repository'),
    (r'src\utils\diagLogs.ts', 'FIXED: analytics.py - Diagnostic logs'),
    (r'src\utils\directMemberMessage.ts', 'FIXED: hooks_system.py - Direct member message'),
    (r'src\utils\displayTags.ts', 'FIXED: cli_utils.py - Display tags'),
    (r'src\utils\doctorContextWarnings.ts', 'FIXED: cli_utils.py - Doctor context warnings'),
    (r'src\utils\doctorDiagnostic.ts', 'FIXED: cli_utils.py - Doctor diagnostic'),
    (r'src\utils\earlyInput.ts', 'FIXED: hooks_system.py - Early input'),
    (r'src\utils\editor.ts', 'FIXED: cli_utils.py - Editor utilities'),
    (r'src\utils\effort.ts', 'FIXED: analytics.py - Effort utilities'),
    (r'src\utils\embeddedTools.ts', 'FIXED: enhanced_types.py - Embedded tools'),
    (r'src\utils\envDynamic.ts', 'FIXED: subprocess_env.py - Dynamic env'),
    (r'src\utils\envUtils.ts', 'FIXED: subprocess_env.py - Env utilities'),
    (r'src\utils\envValidation.ts', 'FIXED: subprocess_env.py - Env validation'),
]

updated = 0
for path, fix in fixes:
    c.execute('UPDATE files SET notes = COALESCE(notes, \'\') || ? WHERE src_path = ?', (f' | {fix}', path))
    if c.rowcount > 0:
        updated += 1

conn.commit()
print(f'Updated {updated} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()