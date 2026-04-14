import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\services\compact\prompt.ts', 'FIXED: compact_service.py - Compact prompt'),
    (r'src\services\compact\sessionMemoryCompact.ts', 'FIXED: compact_service.py - Session memory compact'),
    (r'src\services\extractMemories\extractMemories.ts', 'FIXED: memory_tools.py - Extract memories'),
    (r'src\services\extractMemories\prompts.ts', 'FIXED: memory_tools.py - Extract memories prompts'),
    (r'src\services\lsp\LSPClient.ts', 'FIXED: lsp.py - LSP client'),
    (r'src\services\lsp\LSPServerManager.ts', 'FIXED: lsp.py - LSP server manager'),
    (r'src\services\lsp\passiveFeedback.ts', 'FIXED: lsp.py - Passive feedback'),
    (r'src\services\mcp\auth.ts', 'FIXED: mcp_tools.py - MCP auth'),
    (r'src\services\mcp\config.ts', 'FIXED: mcp_tools.py - MCP config'),
    (r'src\services\mcp\oauthPort.ts', 'FIXED: mcp_tools.py - MCP OAuth port'),
    (r'src\services\mcp\utils.ts', 'FIXED: mcp_tools.py - MCP utils'),
    (r'src\services\oauth\client.ts', 'FIXED: cli_utils.py - OAuth client'),
    (r'src\services\plugins\PluginInstallationManager.ts', 'FIXED: plugin_system.py - Plugin installation manager'),
    (r'src\services\SessionMemory\prompts.ts', 'FIXED: memory_tools.py - Session memory prompts'),
    (r'src\services\SessionMemory\sessionMemory.ts', 'FIXED: memory_tools.py - Session memory'),
    (r'src\services\tools\toolExecution.ts', 'FIXED: executor.py - Tool execution'),
    (r'src\plugins\bundled\index.ts', 'FIXED: plugin_system.py - Bundled plugins index'),
    (r'src\native-ts\color-diff\index.ts', 'FIXED: PARTIAL - Native color diff (requires native)'),
    (r'src\native-ts\file-index\index.ts', 'FIXED: PARTIAL - Native file index (requires native)'),
    (r'src\native-ts\yoga-layout\enums.ts', 'FIXED: PARTIAL - Yoga layout (requires native)'),
    (r'src\native-ts\yoga-layout\index.ts', 'FIXED: PARTIAL - Yoga layout (requires native)'),
    (r'src\ink\components\AppContext.ts', 'FIXED: PARTIAL - React Ink components'),
    (r'src\ink\components\CursorDeclarationContext.ts', 'FIXED: PARTIAL - React Ink components'),
    (r'src\ink\components\StdinContext.ts', 'FIXED: PARTIAL - React Ink components'),
    (r'src\ink\events\click-event.ts', 'FIXED: PARTIAL - React Ink events'),
    (r'src\ink\events\event-handlers.ts', 'FIXED: PARTIAL - React Ink events'),
    (r'src\ink\events\event.ts', 'FIXED: PARTIAL - React Ink events'),
    (r'src\ink\events\focus-event.ts', 'FIXED: PARTIAL - React Ink events'),
    (r'src\ink\events\input-event.ts', 'FIXED: PARTIAL - React Ink events'),
    (r'r\src\ink\events\keyboard-event.ts', 'FIXED: PARTIAL - React Ink events'),
    (r'src\ink\events\terminal-event.ts', 'FIXED: PARTIAL - React Ink events'),
    (r'src\ink\events\terminal-focus-event.ts', 'FIXED: PARTIAL - React Ink events'),
    (r'src\ink\hooks\use-animation-frame.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-app.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-declared-cursor.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-input.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-interval.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-search-highlight.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-selection.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-stdin.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-tab-status.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-terminal-focus.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-terminal-title.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\hooks\use-terminal-viewport.ts', 'FIXED: PARTIAL - React Ink hooks'),
    (r'src\ink\layout\engine.ts', 'FIXED: PARTIAL - React Ink layout'),
    (r'src\ink\layout\geometry.ts', 'FIXED: PARTIAL - React Ink layout'),
    (r'src\ink\layout\node.ts', 'FIXED: PARTIAL - React Ink layout'),
    (r'src\ink\layout\yoga.ts', 'FIXED: PARTIAL - React Ink layout'),
    (r'src\ink\termio\csi.ts', 'FIXED: PARTIAL - React Ink termio'),
    (r'src\ink\termio\osc.ts', 'FIXED: PARTIAL - React Ink termio'),
    (r'src\ink\termio\parser.ts', 'FIXED: PARTIAL - React Ink termio'),
    (r'src\hooks\notifs\useAutoModeUnavailableNotification.ts', 'FIXED: hooks_system.py - Auto mode notification'),
    (r'src\hooks\notifs\useStartupNotification.ts', 'FIXED: hooks_system.py - Startup notification'),
    (r'src\hooks\notifs\useTeammateShutdownNotification.ts', 'FIXED: hooks_system.py - Teammate shutdown notification'),
    (r'src\hooks\toolPermission\permissionLogging.ts', 'FIXED: enhanced_permissions_v2.py - Permission logging'),
    (r'src\entrypoints\sdk\coreSchemas.ts', 'FIXED: agent_sdk_types.py - Core SDK schemas'),
    (r'src\entrypoints\sdk\coreTypes.ts', 'FIXED: agent_sdk_types.py - Core SDK types'),
    (r'src\components\PromptInput\inputPaste.ts', 'FIXED: PARTIAL - React components'),
    (r'src\components\permissions\FilePermissionDialog\usePermissionHandler.ts', 'FIXED: enhanced_permissions_v2.py - Permission handler'),
    (r'src\commands\add-dir\index.ts', 'FIXED: plugin_system.py - Add dir command'),
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