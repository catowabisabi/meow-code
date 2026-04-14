import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\remote\remotePermissionBridge.ts', 'PARTIAL: NO_MATCH - Synthetic message creation for CCR requires native integration'),
    (r'src\remote\RemoteSessionManager.ts', 'PARTIAL: NO_MATCH - Remote session lifecycle management requires native CCR'),
    (r'src\schemas\hooks.ts', 'PARTIAL: NO_MATCH - Pydantic schemas for hook types not fully implemented'),
    (r'src\server\types.ts', 'PARTIAL: NO_MATCH - Direct connect response schema not implemented'),
    (r'src\state\selectors.ts', 'PARTIAL: NO_MATCH - UI-specific selectors (React state)'),
    (r'src\state\teammateViewHelpers.ts', 'PARTIAL: NO_MATCH - Pure UI panel logic'),
    (r'src\utils\gitDiff.ts', 'PARTIAL: NO_MATCH - Structured diff parsing not implemented'),
    (r'src\voice\voiceModeEnabled.ts', 'PARTIAL: NO_MATCH - Voice auth/feature-gate not implemented'),
    (r'src\utils\bash\ast.ts', 'PARTIAL: NO_MATCH - AST-based parsing requires tree-sitter native binding'),
    (r'src\utils\bash\parser.ts', 'PARTIAL: NO_MATCH - tree-sitter parser requires native binding'),
    (r'src\utils\git\gitConfigParser.ts', 'PARTIAL: Could implement with configparser'),
    (r'src\utils\model\bedrock.ts', 'PARTIAL: NO_MATCH - Bedrock support not implemented'),
    (r'src\utils\model\configs.ts', 'PARTIAL: Could implement per-provider model mappings'),
    (r'src\utils\model\modelCapabilities.ts', 'PARTIAL: NO_MATCH - Capability introspection not implemented'),
    (r'src\utils\model\modelOptions.ts', 'PARTIAL: NO_MATCH - Dynamic model options not implemented'),
    (r'src\utils\permissions\dangerousPatterns.ts', 'FIXED: enhanced_permissions_v2.py - Dangerous pattern detection'),
    (r'src\utils\plugins\mcpPluginIntegration.ts', 'FIXED: lsp.py - MCP plugin integration'),
    (r'src\utils\swarm\constants.ts', 'FIXED: remote_swarm.py - Swarm constants'),
    (r'src\utils\swarm\reconnection.ts', 'PARTIAL: NO_MATCH - Teammate reconnection not implemented'),
    (r'src\utils\swarm\teamHelpers.ts', 'PARTIAL: NO_MATCH - Team file management not implemented'),
    (r'src\utils\swarm\teammateInit.ts', 'PARTIAL: NO_MATCH - Idle notification not implemented'),
    (r'src\utils\telemetry\events.ts', 'FIXED: analytics.py - Telemetry events'),
    (r'src\tools\AgentTool\agentToolUtils.ts', 'FIXED: enhanced_agent.py - Agent tool utils'),
    (r'src\tools\AgentTool\builtInAgents.ts', 'FIXED: enhanced_agent.py - Built-in agents registry'),
    (r'src\tools\AgentTool\forkSubagent.ts', 'PARTIAL: NO_MATCH - Fork subagent not implemented'),
    (r'src\tools\AgentTool\loadAgentsDir.ts', 'FIXED: enhanced_agent.py - Agent directory loading'),
    (r'src\services\api\overageCreditGrant.ts', 'FIXED: analytics.py - Overage credit formatting'),
    (r'src\services\MagicDocs\magicDocs.ts', 'PARTIAL: NO_MATCH - Magic Docs not implemented'),
    (r'src\services\oauth\auth-code-listener.ts', 'PARTIAL: NO_MATCH - OAuth flow differs'),
    (r'src\services\oauth\crypto.ts', 'FIXED: cli_utils.py - OAuth crypto'),
    (r'src\services\PromptSuggestion\promptSuggestion.ts', 'PARTIAL: NO_MATCH - Prompt suggestion not implemented'),
    (r'src\services\remoteManagedSettings\index.ts', 'PARTIAL: NO_MATCH - Remote managed settings not implemented'),
    (r'src\services\settingsSync\index.ts', 'PARTIAL: NO_MATCH - Settings sync not implemented'),
    (r'src\services\tips\tipRegistry.ts', 'PARTIAL: NO_MATCH - Tips registry not implemented'),
    (r'src\services\tools\toolHooks.ts', 'FIXED: hooks_system.py - Tool hooks'),
    (r'src\services\tools\toolOrchestration.ts', 'PARTIAL: NO_MATCH - Tool orchestration not implemented'),
    (r'src\dialogLaunchers.tsx', 'PARTIAL: NO_MATCH - Ink-based TUI dialogs (React)'),
    (r'src\hooks\useCanUseTool.tsx', 'PARTIAL: NO_MATCH - TUI permission state machine (React)'),
]

updated = 0
for path, fix in fixes:
    try:
        c.execute('UPDATE files SET notes = ? WHERE src_path = ?', (fix, path))
        if c.rowcount > 0:
            updated += 1
    except Exception as e:
        print(f'Error updating {path}: {e}')

conn.commit()
print(f'Updated {updated} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
print(f'FIXED: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%PARTIAL:%' OR notes LIKE '%NO_MATCH:%'")
print(f'PARTIAL/NO_MATCH: {c.fetchone()[0]}')

conn.close()