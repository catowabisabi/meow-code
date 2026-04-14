import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\commands.ts', 'FIXED: commands.py - FeatureGatedCommand, CommandContext, command decorators'),
    ('src\\context.ts', 'FIXED: Added CLAUDE.md discovery in cli_utils.py'),
    ('src\\cost-tracker.ts', 'FIXED: analytics.py - CostTracker with model-specific pricing'),
    ('src\\history.ts', 'FIXED: enhanced_shell.py - PasteStore with hash references'),
    ('src\\projectOnboardingState.ts', 'FIXED: cli_utils.py - ProjectOnboardingState machine'),
    ('src\\setup.ts', 'FIXED: commands.py - SetupCommand with tmux integration'),
    ('src\\Task.ts', 'FIXED: task_tools.py - TaskState tracking'),
    ('src\\tools.ts', 'FIXED: enhanced_types.py - feature-gated tool filtering'),
    ('src\\assistant\\sessionHistory.ts', 'FIXED: compact_service.py - SessionHistory storage'),
    ('src\\bootstrap\\state.ts', 'FIXED: analytics.py - AttributedCounter, cron task tracking'),
    ('src\\bridge\\bridgeConfig.ts', 'FIXED: enhanced_bridge.py - BridgeConfig with override pattern'),
    ('src\\bridge\\bridgeDebug.ts', 'FIXED: cli_utils.py - FaultInjectionFramework'),
    ('src\\bridge\\bridgeEnabled.ts', 'FIXED: enhanced_settings.py - GrowthBook client integration'),
    ('src\\bridge\\bridgeMain.ts', 'FIXED: enhanced_bridge.py - BridgeDaemon subprocess management'),
    ('src\\bridge\\bridgeMessaging.ts', 'FIXED: enhanced_bridge.py - SDK message parsing, control requests'),
    ('src\\bridge\\bridgePermissionCallbacks.ts', 'FIXED: enhanced_permissions_v2.py - PermissionCallback types'),
    ('src\\bridge\\bridgePointer.ts', 'FIXED: enhanced_bridge.py - CrashRecoveryPointer'),
    ('src\\bridge\\bridgeStatusUtil.ts', 'FIXED: cli_utils.py - TerminalUI animations'),
    ('src\\bridge\\bridgeUI.ts', 'FIXED: cli_utils.py - TerminalUI capabilities'),
    ('src\\bridge\\capacityWake.ts', 'FIXED: transports.py - AbortSignal equivalent via asyncio'),
    ('src\\bridge\\codeSessionApi.ts', 'FIXED: api_server/routes/sessions.py - CCR v2 API'),
    ('src\\bridge\\createSession.ts', 'FIXED: enhanced_bridge.py - Bridge session creation with git context'),
    ('src\\bridge\\debugUtils.ts', 'FIXED: powershell_security.py - Redaction utilities'),
    ('src\\bridge\\envLessBridgeConfig.ts', 'FIXED: enhanced_settings.py - GrowthBook-driven bridge config'),
    ('src\\bridge\\flushGate.ts', 'FIXED: transports.py - FlushGate mechanism'),
    ('src\\bridge\\inboundAttachments.ts', 'FIXED: enhanced_bridge.py - File attachment resolution'),
    ('src\\bridge\\inboundMessages.ts', 'FIXED: enhanced_bridge.py - Inbound message content extraction'),
    ('src\\bridge\\initReplBridge.ts', 'FIXED: repl.py - Bridge initialization flow'),
    ('src\\bridge\\pollConfig.ts', 'FIXED: enhanced_bridge.py - Dynamic poll interval configuration'),
    ('src\\bridge\\pollConfigDefaults.ts', 'FIXED: enhanced_bridge.py - Polling configuration defaults'),
    ('src\\bridge\\remoteBridgeCore.ts', 'FIXED: enhanced_bridge.py - Env-less bridge path'),
    ('src\\bridge\\replBridge.ts', 'FIXED: repl.py - REPL bridge implementation'),
    ('src\\bridge\\replBridgeHandle.ts', 'FIXED: repl.py - GlobalBridgeHandle'),
    ('src\\bridge\\replBridgeTransport.ts', 'FIXED: transports.py - SSE/WebSocket transport adapters'),
    ('src\\bridge\\sessionIdCompat.ts', 'FIXED: enhanced_bridge.py - SessionID compatibility layer'),
    ('src\\bridge\\trustedDevice.ts', 'FIXED: enhanced_permissions_v2.py - TrustedDeviceFlow'),
    ('src\\bridge\\types.ts', 'FIXED: enhanced_bridge.py - BridgeState, SessionSpawner, BridgeLogger'),
    ('src\\bridge\\workSecret.ts', 'FIXED: enhanced_bridge.py - WorkSecret decoding/version validation'),
    ('src\\buddy\\companion.ts', 'FIXED: companion.py - Companion generation system (placeholder)'),
    ('src\\buddy\\prompt.ts', 'FIXED: companion.py - Companion intro generation'),
    ('src\\buddy\\sprites.ts', 'FIXED: companion.py - ASCII sprite data'),
    ('src\\buddy\\types.ts', 'FIXED: companion.py - Companion type definitions'),
    ('src\\cli\\ndjsonSafeStringify.ts', 'FIXED: cli_utils.py - NDJSON safe stringifier'),
    ('src\\cli\\remoteIO.ts', 'FIXED: transports.py - Remote IO streaming'),
    ('src\\cli\\structuredIO.ts', 'FIXED: cli_utils.py - StructuredIO'),
    ('src\\cli\\update.ts', 'FIXED: cli_utils.py - SelfUpdate command'),
    ('src\\history.ts', 'FIXED: shell.py - PasteStore hash references'),
    ('src\\query.ts', 'FIXED: query_engine.py - streaming tool execution, reactive compact, media recovery'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()