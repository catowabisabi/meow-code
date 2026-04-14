import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\remote\SessionsWebSocket.ts', 'FIXED: transports.py - SessionsWebSocket'),
    (r'src\services\awaySummary.ts', 'FIXED: hooks_system.py - AwaySummary service'),
    (r'src\services\claudeAiLimitsHook.ts', 'FIXED: model_routing.py - ClaudeAI limits hook'),
    (r'src\services\diagnosticTracking.ts', 'FIXED: analytics.py - Diagnostic tracking'),
    (r'src\services\internalLogging.ts', 'FIXED: cli_utils.py - Internal logging'),
    (r'src\services\mockRateLimits.ts', 'FIXED: model_routing.py - Mock rate limits'),
    (r'src\services\notifier.ts', 'FIXED: hooks_system.py - Notifier service'),
    (r'src\services\preventSleep.ts', 'FIXED: cli_utils.py - Prevent sleep'),
    (r'src\services\rateLimitMessages.ts', 'FIXED: model_routing.py - Rate limit messages'),
    (r'src\services\rateLimitMocking.ts', 'FIXED: model_routing.py - Rate limit mocking'),
    (r'src\services\tokenEstimation.ts', 'FIXED: analytics.py - Token estimation'),
    (r'src\services\vcr.ts', 'FIXED: hooks_system.py - VCR service'),
    (r'src\services\voice.ts', 'FIXED: terminal_voice.py - Voice service'),
    (r'src\services\voiceKeyterms.ts', 'FIXED: terminal_voice.py - Voice keyterms'),
    (r'src\services\voiceStreamSTT.ts', 'FIXED: terminal_voice.py - Voice stream STT'),
    (r'src\skills\bundledSkills.ts', 'FIXED: skill_tool.py - Bundled skills'),
    (r'src\skills\loadSkillsDir.ts', 'FIXED: skill_tool.py - Load skills directory'),
    (r'src\skills\mcpSkillBuilders.ts', 'FIXED: mcp_tools.py - MCP skill builders'),
    (r'src\state\store.ts', 'FIXED: compact_service.py - State store'),
    (r'src\tasks\LocalMainSessionTask.ts', 'FIXED: task_tools.py - Local main session task'),
    (r'src\tasks\pillLabel.ts', 'FIXED: cli_utils.py - Task pill label'),
    (r'src\tasks\stopTask.ts', 'FIXED: task_stop.py - Stop task'),
    (r'src\tasks\types.ts', 'FIXED: task_tools.py - Task types'),
    (r'src\tools\utils.ts', 'FIXED: enhanced_types.py - Tool utilities'),
    (r'src\types\hooks.ts', 'FIXED: hooks_system.py - Hook types'),
    (r'src\types\ids.ts', 'FIXED: cli_utils.py - ID types'),
    (r'src\types\logs.ts', 'FIXED: cli_utils.py - Log types'),
    (r'src\types\permissions.ts', 'FIXED: enhanced_permissions_v2.py - Permission types'),
    (r'src\types\plugin.ts', 'FIXED: plugin_system.py - Plugin types'),
    (r'src\types\textInputTypes.ts', 'FIXED: hooks_system.py - Text input types'),
    (r'src\utils\abortController.ts', 'FIXED: transports.py - AbortController'),
    (r'src\utils\activityManager.ts', 'FIXED: analytics.py - Activity manager'),
    (r'src\utils\advisor.ts', 'FIXED: commands.py - Advisor utility'),
    (r'src\utils\agentContext.ts', 'FIXED: enhanced_agent.py - Agent context'),
    (r'src\utils\agentId.ts', 'FIXED: cli_utils.py - Agent ID'),
    (r'src\utils\agentSwarmsEnabled.ts', 'FIXED: remote_swarm.py - Agent swarms enabled'),
    (r'src\utils\analyzeContext.ts', 'FIXED: cli_utils.py - Analyze context'),
    (r'src\utils\ansiToPng.ts', 'FIXED: PARTIAL - React Ink ANSI to PNG'),
    (r'src\utils\ansiToSvg.ts', 'FIXED: PARTIAL - React Ink ANSI to SVG'),
    (r'src\utils\api.ts', 'FIXED: webfetch_tool.py - API utilities'),
    (r'src\utils\apiPreconnect.ts', 'FIXED: webfetch_tool.py - API preconnect'),
    (r'src\utils\appleTerminalBackup.ts', 'FIXED: cli_utils.py - Apple terminal backup'),
    (r'src\utils\argumentSubstitution.ts', 'FIXED: bash.py - Argument substitution'),
    (r'src\utils\array.ts', 'FIXED: cli_utils.py - Array utilities'),
    (r'src\utils\asciicast.ts', 'FIXED: cli_utils.py - Asciicast'),
    (r'src\utils\attachments.ts', 'FIXED: webfetch_tool.py - Attachments'),
    (r'src\utils\attribution.ts', 'FIXED: analytics.py - Attribution'),
    (r'src\utils\auth.ts', 'FIXED: enhanced_permissions_v2.py - Auth utilities'),
    (r'src\utils\authFileDescriptor.ts', 'FIXED: cli_utils.py - Auth file descriptor'),
    (r'src\utils\authPortable.ts', 'FIXED: cli_utils.py - Auth portable'),
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