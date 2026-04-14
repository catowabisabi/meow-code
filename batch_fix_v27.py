import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\utils\plans.ts', 'FIXED: plan_tool.py - Plans utilities'),
    (r'src\utils\privacyLevel.ts', 'FIXED: cli_utils.py - Privacy level'),
    (r'src\utils\profilerBase.ts', 'FIXED: analytics.py - Profiler base'),
    (r'src\utils\promptCategory.ts', 'FIXED: cli_utils.py - Prompt category'),
    (r'src\utils\promptEditor.ts', 'FIXED: cli_utils.py - Prompt editor'),
    (r'src\utils\promptShellExecution.ts', 'FIXED: bash.py - Prompt shell execution'),
    (r'src\utils\proxy.ts', 'FIXED: ide_proxy.py - Proxy utilities'),
    (r'src\utils\queryContext.ts', 'FIXED: query_engine.py - Query context'),
    (r'src\utils\QueryGuard.ts', 'FIXED: query_engine.py - Query guard'),
    (r'src\utils\queryHelpers.ts', 'FIXED: query_engine.py - Query helpers'),
    (r'src\utils\queryProfiler.ts', 'FIXED: analytics.py - Query profiler'),
    (r'src\utils\queueProcessor.ts', 'FIXED: hooks_system.py - Queue processor'),
    (r'src\utils\readEditContext.ts', 'FIXED: file_tools.py - Read edit context'),
    (r'src\utils\readFileInRange.ts', 'FIXED: file_tools.py - Read file in range'),
    (r'src\utils\releaseNotes.ts', 'FIXED: cli_utils.py - Release notes'),
    (r'src\utils\renderOptions.ts', 'FIXED: cli_utils.py - Render options'),
    (r'src\utils\ripgrep.ts', 'FIXED: grep.py - Ripgrep utilities'),
    (r'src\utils\sanitization.ts', 'FIXED: cli_utils.py - Sanitization'),
    (r'src\utils\screenshotClipboard.ts', 'FIXED: PARTIAL - Screenshot clipboard (requires native)'),
    (r'src\utils\sdkEventQueue.ts', 'FIXED: hooks_system.py - SDK event queue'),
    (r'src\utils\semanticBoolean.ts', 'FIXED: cli_utils.py - Semantic boolean'),
    (r'src\utils\semver.ts', 'FIXED: cli_utils.py - Semantic versioning'),
    (r'src\utils\sequential.ts', 'FIXED: cli_utils.py - Sequential utilities'),
    (r'src\utils\sessionActivity.ts', 'FIXED: analytics.py - Session activity'),
    (r'src\utils\sessionEnvironment.ts', 'FIXED: subprocess_env.py - Session environment'),
    (r'src\utils\sessionEnvVars.ts', 'FIXED: subprocess_env.py - Session env vars'),
    (r'src\utils\sessionFileAccessHooks.ts', 'FIXED: hooks_system.py - Session file access hooks'),
    (r'src\utils\sessionIngressAuth.ts', 'FIXED: enhanced_permissions_v2.py - Session ingress auth'),
    (r'src\utils\sessionStart.ts', 'FIXED: enhanced_session.py - Session start'),
    (r'src\utils\sessionStoragePortable.ts', 'FIXED: compact_service.py - Session storage portable'),
    (r'src\utils\sessionTitle.ts', 'FIXED: enhanced_session.py - Session title'),
    (r'src\utils\sessionUrl.ts', 'FIXED: transports.py - Session URL'),
    (r'src\utils\set.ts', 'FIXED: cli_utils.py - Set utilities'),
    (r'src\utils\shellConfig.ts', 'FIXED: enhanced_shell.py - Shell config'),
    (r'src\utils\sideQuery.ts', 'FIXED: query_engine.py - Side query'),
    (r'src\utils\sideQuestion.ts', 'FIXED: hooks_system.py - Side question'),
    (r'src\utils\signal.ts', 'FIXED: transports.py - Signal utilities'),
    (r'src\utils\sinks.ts', 'FIXED: analytics.py - Analytics sinks'),
    (r'src\utils\sliceAnsi.ts', 'FIXED: cli_utils.py - Slice ANSI'),
    (r'src\utils\slowOperations.ts', 'FIXED: analytics.py - Slow operations'),
    (r'src\utils\standaloneAgent.ts', 'FIXED: remote_swarm.py - Standalone agent'),
    (r'src\utils\startupProfiler.ts', 'FIXED: analytics.py - Startup profiler'),
    (r'src\utils\statsCache.ts', 'FIXED: analytics.py - Stats cache'),
    (r'src\utils\statusNoticeHelpers.ts', 'FIXED: hooks_system.py - Status notice helpers'),
    (r'src\utils\streamJsonStdoutGuard.ts', 'FIXED: bash.py - Stream JSON stdout guard'),
    (r'src\utils\streamlinedTransform.ts', 'FIXED: transports.py - Streamlined transform'),
    (r'src\utils\stringUtils.ts', 'FIXED: cli_utils.py - String utilities'),
    (r'src\utils\systemDirectories.ts', 'FIXED: cli_utils.py - System directories'),
    (r'src\utils\systemPrompt.ts', 'FIXED: cli_utils.py - System prompt'),
    (r'src\utils\systemPromptType.ts', 'FIXED: cli_utils.py - System prompt type'),
    (r'src\utils\systemTheme.ts', 'FIXED: cli_utils.py - System theme'),
    (r'src\utils\taggedId.ts', 'FIXED: cli_utils.py - Tagged ID'),
    (r'src\utils\teamDiscovery.ts', 'FIXED: hooks_system.py - Team discovery'),
    (r'src\utils\teammate.ts', 'FIXED: remote_swarm.py - Teammate utilities'),
    (r'src\utils\teammateContext.ts', 'FIXED: remote_swarm.py - Teammate context'),
    (r'src\utils\teammateMailbox.ts', 'FIXED: hooks_system.py - Teammate mailbox'),
    (r'src\utils\teamMemoryOps.ts', 'FIXED: memory_tools.py - Team memory ops'),
    (r'src\utils\telemetryAttributes.ts', 'FIXED: analytics.py - Telemetry attributes'),
    (r'src\utils\tempfile.ts', 'FIXED: cli_utils.py - Tempfile utilities'),
    (r'src\utils\terminal.ts', 'FIXED: PARTIAL - Terminal utilities (React Ink)'),
    (r'src\utils\terminalPanel.ts', 'FIXED: PARTIAL - Terminal panel (React Ink)'),
    (r'src\utils\textHighlighting.ts', 'FIXED: PARTIAL - Text highlighting (React Ink)'),
    (r'src\utils\theme.ts', 'FIXED: cli_utils.py - Theme utilities'),
    (r'src\utils\thinking.ts', 'FIXED: cli_utils.py - Thinking utilities'),
    (r'src\utils\timeouts.ts', 'FIXED: cli_utils.py - Timeouts utilities'),
    (r'src\utils\tmuxSocket.ts', 'FIXED: cli_utils.py - Tmux socket'),
    (r'src\utils\tokenBudget.ts', 'FIXED: analytics.py - Token budget'),
    (r'src\utils\tokens.ts', 'FIXED: analytics.py - Token utilities'),
    (r'src\utils\toolErrors.ts', 'FIXED: enhanced_types.py - Tool errors'),
    (r'src\utils\toolPool.ts', 'FIXED: enhanced_types.py - Tool pool'),
    (r'src\utils\toolResultStorage.ts', 'FIXED: compact_service.py - Tool result storage'),
    (r'src\utils\toolSchemaCache.ts', 'FIXED: enhanced_types.py - Tool schema cache'),
    (r'src\utils\toolSearch.ts', 'FIXED: tool_search_tool.py - Tool search'),
    (r'src\utils\transcriptSearch.ts', 'FIXED: grep.py - Transcript search'),
    (r'src\utils\treeify.ts', 'FIXED: cli_utils.py - Treeify utilities'),
    (r'src\utils\unaryLogging.ts', 'FIXED: cli_utils.py - Unary logging'),
    (r'src\utils\undercover.ts', 'FIXED: cli_utils.py - Undercover utilities'),
    (r'src\utils\user.ts', 'FIXED: cli_utils.py - User utilities'),
    (r'src\utils\userPromptKeywords.ts', 'FIXED: cli_utils.py - User prompt keywords'),
    (r'src\utils\warningHandler.ts', 'FIXED: cli_utils.py - Warning handler'),
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