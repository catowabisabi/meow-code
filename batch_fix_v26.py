import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\utils\errorLogSink.ts', 'FIXED: cli_utils.py - Error log sink'),
    (r'src\utils\execFileNoThrow.ts', 'FIXED: bash.py - Exec file no throw'),
    (r'src\utils\execFileNoThrowPortable.ts', 'FIXED: bash.py - Exec file no throw portable'),
    (r'src\utils\execSyncWrapper.ts', 'FIXED: bash.py - Exec sync wrapper'),
    (r'src\utils\extraUsage.ts', 'FIXED: analytics.py - Extra usage'),
    (r'src\utils\fastMode.ts', 'FIXED: cli_utils.py - Fast mode'),
    (r'src\utils\file.ts', 'FIXED: file_tools.py - File utilities'),
    (r'src\utils\fileHistory.ts', 'FIXED: shell.py - File history'),
    (r'src\utils\fileOperationAnalytics.ts', 'FIXED: analytics.py - File operation analytics'),
    (r'src\utils\fileRead.ts', 'FIXED: file_tools.py - File read'),
    (r'src\utils\fileReadCache.ts', 'FIXED: file_tools.py - File read cache'),
    (r'src\utils\fileStateCache.ts', 'FIXED: cli_utils.py - File state cache'),
    (r'src\utils\findExecutable.ts', 'FIXED: cli_utils.py - Find executable'),
    (r'src\utils\fingerprint.ts', 'FIXED: cli_utils.py - Fingerprint'),
    (r'src\utils\forkedAgent.ts', 'FIXED: remote_swarm.py - Forked agent'),
    (r'src\utils\format.ts', 'FIXED: cli_utils.py - Format utilities'),
    (r'src\utils\formatBriefTimestamp.ts', 'FIXED: cli_utils.py - Format brief timestamp'),
    (r'src\utils\fpsTracker.ts', 'FIXED: analytics.py - FPS tracker'),
    (r'src\utils\frontmatterParser.ts', 'FIXED: cli_utils.py - Frontmatter parser'),
    (r'src\utils\fsOperations.ts', 'FIXED: file_tools.py - FS operations'),
    (r'src\utils\fullscreen.ts', 'FIXED: cli_utils.py - Fullscreen utilities'),
    (r'src\utils\generatedFiles.ts', 'FIXED: cli_utils.py - Generated files'),
    (r'src\utils\generators.ts', 'FIXED: cli_utils.py - Generators'),
    (r'src\utils\genericProcessUtils.ts', 'FIXED: bash.py - Generic process utils'),
    (r'src\utils\getWorktreePaths.ts', 'FIXED: worktree_tools.py - Get worktree paths'),
    (r'src\utils\getWorktreePathsPortable.ts', 'FIXED: worktree_tools.py - Get worktree paths portable'),
    (r'src\utils\ghPrStatus.ts', 'FIXED: git_fs.py - GH PR status'),
    (r'src\utils\git.ts', 'FIXED: git_fs.py - Git utilities'),
    (r'src\utils\githubRepoPathMapping.ts', 'FIXED: git_fs.py - GitHub repo path mapping'),
    (r'src\utils\gitSettings.ts', 'FIXED: git_fs.py - Git settings'),
    (r'src\utils\glob.ts', 'FIXED: glob_tool.py - Glob utilities'),
    (r'src\utils\gracefulShutdown.ts', 'FIXED: cli_utils.py - Graceful shutdown'),
    (r'src\utils\groupToolUses.ts', 'FIXED: analytics.py - Group tool uses'),
    (r'src\utils\handlePromptSubmit.ts', 'FIXED: hooks_system.py - Handle prompt submit'),
    (r'src\utils\headlessProfiler.ts', 'FIXED: analytics.py - Headless profiler'),
    (r'src\utils\heapDumpService.ts', 'FIXED: cli_utils.py - Heap dump service'),
    (r'src\utils\heatmap.ts', 'FIXED: analytics.py - Heatmap utilities'),
    (r'src\utils\hooks.ts', 'FIXED: hooks_system.py - Hook utilities'),
    (r'src\utils\horizontalScroll.ts', 'FIXED: cli_utils.py - Horizontal scroll'),
    (r'src\utils\hyperlink.ts', 'FIXED: cli_utils.py - Hyperlink utilities'),
    (r'src\utils\idePathConversion.ts', 'FIXED: ide_proxy.py - IDE path conversion'),
    (r'src\utils\idleTimeout.ts', 'FIXED: cli_utils.py - Idle timeout'),
    (r'src\utils\imagePaste.ts', 'FIXED: cli_utils.py - Image paste'),
    (r'src\utils\imageResizer.ts', 'FIXED: cli_utils.py - Image resizer'),
    (r'src\utils\imageStore.ts', 'FIXED: cli_utils.py - Image store'),
    (r'src\utils\ink.ts', 'FIXED: PARTIAL - React Ink utilities'),
    (r'src\utils\inProcessTeammateHelpers.ts', 'FIXED: hooks_system.py - In-process teammate helpers'),
    (r'src\utils\intl.ts', 'FIXED: cli_utils.py - Internationalization'),
    (r'src\utils\iTermBackup.ts', 'FIXED: cli_utils.py - iTerm backup'),
    (r'src\utils\jetbrains.ts', 'FIXED: ide_proxy.py - JetBrains utilities'),
    (r'src\utils\jsonRead.ts', 'FIXED: cli_utils.py - JSON read'),
    (r'src\utils\keyboardShortcuts.ts', 'FIXED: cli_utils.py - Keyboard shortcuts'),
    (r'src\utils\lazySchema.ts', 'FIXED: cli_utils.py - Lazy schema'),
    (r'src\utils\listSessionsImpl.ts', 'FIXED: compact_service.py - List sessions implementation'),
    (r'src\utils\localInstaller.ts', 'FIXED: cli_utils.py - Local installer'),
    (r'src\utils\lockfile.ts', 'FIXED: cron_scheduler.py - Lockfile'),
    (r'src\utils\logoV2Utils.ts', 'FIXED: cli_utils.py - Logo V2 utils'),
    (r'src\utils\mailbox.ts', 'FIXED: hooks_system.py - Mailbox utilities'),
    (r'src\utils\managedEnv.ts', 'FIXED: subprocess_env.py - Managed env'),
    (r'src\utils\managedEnvConstants.ts', 'FIXED: subprocess_env.py - Managed env constants'),
    (r'src\utils\markdownConfigLoader.ts', 'FIXED: cli_utils.py - Markdown config loader'),
    (r'src\utils\mcpInstructionsDelta.ts', 'FIXED: mcp_tools.py - MCP instructions delta'),
    (r'src\utils\mcpOutputStorage.ts', 'FIXED: mcp_tools.py - MCP output storage'),
    (r'src\utils\mcpValidation.ts', 'FIXED: mcp_tools.py - MCP validation'),
    (r'src\utils\mcpWebSocketTransport.ts', 'FIXED: transports.py - MCP WebSocket transport'),
    (r'src\utils\memoize.ts', 'FIXED: cli_utils.py - Memoize utilities'),
    (r'src\utils\memoryFileDetection.ts', 'FIXED: memory_tools.py - Memory file detection'),
    (r'src\utils\messagePredicates.ts', 'FIXED: hooks_system.py - Message predicates'),
    (r'src\utils\messageQueueManager.ts', 'FIXED: hooks_system.py - Message queue manager'),
    (r'src\utils\messages.ts', 'FIXED: cli_utils.py - Messages utilities'),
    (r'src\utils\modelCost.ts', 'FIXED: analytics.py - Model cost'),
    (r'src\utils\modifiers.ts', 'FIXED: cli_utils.py - Modifiers'),
    (r'src\utils\mtls.ts', 'FIXED: subprocess_env.py - mTLS utilities'),
    (r'src\utils\notebook.ts', 'FIXED: notebook_edit_tool.py - Notebook utilities'),
    (r'src\utils\objectGroupBy.ts', 'FIXED: cli_utils.py - Object group by'),
    (r'src\utils\pasteStore.ts', 'FIXED: shell.py - Paste store'),
    (r'src\utils\pdf.ts', 'FIXED: PARTIAL - PDF processing (requires native)'),
    (r'src\utils\pdfUtils.ts', 'FIXED: PARTIAL - PDF utilities (requires native)'),
    (r'src\utils\peerAddress.ts', 'FIXED: transports.py - Peer address'),
    (r'src\utils\planModeV2.ts', 'FIXED: plan_tool.py - Plan mode V2'),
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