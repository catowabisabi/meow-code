import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\services\\mcp\\client.ts', 'FIXED: mcp_tools.py - SseIdeTransport, WsIdeTransport, claudeai proxy'),
    ('src\\commands\\plugin\\pluginDetailsHelpers.tsx', 'FIXED: plugin_system.py - PluginDetailsHelpers'),
    ('src\\utils\\computerUse\\appNames.ts', 'FIXED: cli_utils.py - AppNames'),
    ('src\\services\\claudeAiLimits.ts', 'FIXED: model_routing.py - PolicyLimits with header-based limit detection'),
    ('src\\utils\\hooks\\hooksConfigSnapshot.ts', 'FIXED: cli_utils.py - HooksConfigSnapshot'),
    ('src\\hooks\\useDynamicConfig.ts', 'FIXED: enhanced_settings.py - GrowthBook dynamic config'),
    ('src\\utils\\agenticSessionSearch.ts', 'FIXED: compact_service.py - AgenticSessionSearch with full-text search'),
    ('src\\utils\\tasks.ts', 'FIXED: task_tools.py - Tasks utility'),
    ('src\\utils\\imageValidation.ts', 'FIXED: cli_utils.py - ImageValidation'),
    ('src\\utils\\computerUse\\common.ts', 'FIXED: cli_utils.py - ComputerUseCommon'),
    ('src\\hooks\\useMergedTools.ts', 'FIXED: enhanced_types.py - MergedTools'),
    ('src\\upstreamproxy\\relay.ts', 'FIXED: ide_proxy.py - BinaryRelay with TCP server, CONNECT parser'),
    ('src\\utils\\task\\outputFormatting.ts', 'FIXED: cli_utils.py - OutputFormatting'),
    ('src\\commands\\cost\\cost.ts', 'FIXED: analytics.py - CostCommand'),
    ('src\\utils\\hooks\\hooks.ts', 'FIXED: hooks_system.py - Hook utilities'),
    ('src\\cli\\handlers\\plugins.ts', 'FIXED: plugin_system.py - PluginCLIHandlers'),
    ('src\\utils\\stats.ts', 'FIXED: analytics.py - Stats utilities'),
    ('src\\utils\\truncate.ts', 'FIXED: cli_utils.py - Truncate utility'),
    ('src\\utils\\model\\agent.ts', 'FIXED: model_routing.py - Subagent tier matching'),
    ('src\\state\\onChangeAppState.ts', 'FIXED: cli_utils.py - AppState side effects, OpenTelemetry'),
    ('src\\hooks\\useIDEIntegration.tsx', 'FIXED: ide_proxy.py - IDEIntegration'),
    ('src\\utils\\telemetry\\bigqueryExporter.ts', 'FIXED: analytics.py - BigQueryExporter'),
    ('src\\tools\\BashTool\\bashPermissions.ts', 'FIXED: shell_permissions.py - BashPermissions'),
    ('src\\keybindings\\reservedShortcuts.ts', 'FIXED: cli_utils.py - ReservedShortcuts'),
    ('src\\utils\\messages\\systemInit.ts', 'FIXED: cli_utils.py - SystemInit'),
    ('src\\utils\\nativeInstaller\\packageManagers.ts', 'FIXED: cli_utils.py - PackageManagers'),
    ('src\\commands\\insights.ts', 'FIXED: analytics.py - InsightsCommand with pattern detection'),
    ('src\\utils\\semanticNumber.ts', 'FIXED: cli_utils.py - SemanticNumber'),
    ('src\\tools\\PowerShellTool\\PowerShellTool.tsx', 'FIXED: powershell_tool.py - PowerShellTool'),
    ('src\\ink\\events\\dispatcher.ts', 'FIXED: cli_utils.py - EventDispatcher'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()