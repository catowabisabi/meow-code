import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\utils\plugins\lspPluginIntegration.ts', 'FIXED: lsp.py - LSP plugin integration'),
    (r'src\utils\teleport\api.ts', 'FIXED: PARTIAL - Teleport API (requires native)'),
    (r'src\utils\teleport\environments.ts', 'FIXED: PARTIAL - Teleport environments'),
    (r'src\utils\teleport\environmentSelection.ts', 'FIXED: PARTIAL - Teleport environment selection'),
    (r'src\utils\teleport\gitBundle.ts', 'FIXED: PARTIAL - Teleport git bundle'),
    (r'src\tools\BashTool\readOnlyValidation.ts', 'FIXED: shell_permissions.py - Read-only validation'),
    (r'src\tools\BashTool\sedEditParser.ts', 'FIXED: bash.py - Sed edit parser'),
    (r'src\tools\BashTool\sedValidation.ts', 'FIXED: bash.py - Sed validation'),
    (r'src\tools\BashTool\toolName.ts', 'FIXED: bash.py - Tool name'),
    (r'src\tools\BashTool\utils.ts', 'FIXED: bash.py - Bash tool utils'),
    (r'src\tools\BriefTool\attachments.ts', 'FIXED: brief_tool.py - Brief tool attachments'),
    (r'src\tools\BriefTool\BriefTool.ts', 'FIXED: brief_tool.py - BriefTool'),
    (r'src\tools\BriefTool\upload.ts', 'FIXED: brief_tool.py - Brief tool upload'),
    (r'src\tools\ConfigTool\ConfigTool.ts', 'FIXED: config_tool.py - ConfigTool'),
    (r'src\tools\ConfigTool\constants.ts', 'FIXED: config_tool.py - ConfigTool constants'),
    (r'src\tools\ConfigTool\prompt.ts', 'FIXED: config_tool.py - ConfigTool prompt'),
    (r'src\tools\ConfigTool\supportedSettings.ts', 'FIXED: config_tool.py - Supported settings'),
    (r'src\tools\EnterPlanModeTool\constants.ts', 'FIXED: plan_mode_tools.py - Enter plan mode constants'),
    (r'src\tools\EnterPlanModeTool\EnterPlanModeTool.ts', 'FIXED: plan_mode_tools.py - EnterPlanModeTool'),
    (r'src\tools\EnterPlanModeTool\prompt.ts', 'FIXED: plan_mode_tools.py - Enter plan mode prompt'),
    (r'src\tools\EnterWorktreeTool\constants.ts', 'FIXED: worktree_tools.py - Enter worktree constants'),
    (r'src\tools\EnterWorktreeTool\EnterWorktreeTool.ts', 'FIXED: worktree_tools.py - EnterWorktreeTool'),
    (r'src\tools\EnterWorktreeTool\prompt.ts', 'FIXED: worktree_tools.py - Enter worktree prompt'),
    (r'src\tools\ExitPlanModeTool\ExitPlanModeV2Tool.ts', 'FIXED: plan_mode_tools.py - Exit plan mode V2 tool'),
    (r'src\tools\FileReadTool\FileReadTool.ts', 'FIXED: file_tools.py - FileReadTool'),
    (r'src\tools\FileReadTool\imageProcessor.ts', 'FIXED: file_tools.py - Image processor'),
    (r'src\tools\FileReadTool\limits.ts', 'FIXED: file_tools.py - File read limits'),
    (r'src\tools\GrepTool\GrepTool.ts', 'FIXED: grep.py - GrepTool'),
    (r'src\tools\LSPTool\LSPTool.ts', 'FIXED: lsp_tool.py - LSPTool'),
    (r'src\tools\MCPTool\MCPTool.ts', 'FIXED: mcp_tools.py - MCPTool'),
    (r'src\tools\SkillTool\SkillTool.ts', 'FIXED: skill_tool.py - SkillTool'),
    (r'src\tools\TaskCreateTool\TaskCreateTool.ts', 'FIXED: task_create.py - TaskCreateTool'),
    (r'src\tools\TeamCreateTool\TeamCreateTool.ts', 'FIXED: team_tools.py - TeamCreateTool'),
    (r'src\tools\WebFetchTool\WebFetchTool.ts', 'FIXED: webfetch_tool.py - WebFetchTool'),
    (r'src\tools\AgentTool\built-in\generalPurposeAgent.ts', 'FIXED: enhanced_agent.py - General purpose agent'),
    (r'src\tools\AgentTool\built-in\planAgent.ts', 'FIXED: plan_tool.py - Plan agent'),
    (r'src\tools\AgentTool\built-in\verificationAgent.ts', 'FIXED: enhanced_agent.py - Verification agent'),
    (r'src\services\AgentSummary\agentSummary.ts', 'FIXED: hooks_system.py - Agent summary service'),
    (r'src\services\analytics\growthbook.ts', 'FIXED: analytics.py - GrowthBook analytics'),
    (r'src\services\analytics\index.ts', 'FIXED: analytics.py - Analytics index'),
    (r'src\services\analytics\metadata.ts', 'FIXED: analytics.py - Analytics metadata'),
    (r'src\services\api\adminRequests.ts', 'FIXED: webfetch_tool.py - Admin requests'),
    (r'src\services\api\bootstrap.ts', 'FIXED: webfetch_tool.py - API bootstrap'),
    (r'src\services\api\claude.ts', 'FIXED: webfetch_tool.py - Claude API'),
    (r'src\services\api\client.ts', 'FIXED: webfetch_tool.py - API client'),
    (r'src\services\api\dumpPrompts.ts', 'FIXED: cli_utils.py - Dump prompts'),
    (r'src\services\api\emptyUsage.ts', 'FIXED: analytics.py - Empty usage'),
    (r'src\services\api\errors.ts', 'FIXED: cli_utils.py - API errors'),
    (r'src\services\api\filesApi.ts', 'FIXED: file_tools.py - Files API'),
    (r'src\services\api\firstTokenDate.ts', 'FIXED: analytics.py - First token date'),
    (r'src\services\api\grove.ts', 'FIXED: analytics.py - Grove analytics'),
    (r'src\services\api\logging.ts', 'FIXED: cli_utils.py - API logging'),
    (r'src\services\api\metricsOptOut.ts', 'FIXED: analytics.py - Metrics opt out'),
    (r'src\services\api\referral.ts', 'FIXED: analytics.py - Referral tracking'),
    (r'src\services\api\sessionIngress.ts', 'FIXED: transports.py - Session ingress'),
    (r'src\services\api\ultrareviewQuota.ts', 'FIXED: analytics.py - UltraReview quota'),
    (r'src\services\api\usage.ts', 'FIXED: analytics.py - Usage API'),
    (r'src\services\api\withRetry.ts', 'FIXED: cli_utils.py - With retry'),
    (r'src\services\autoDream\autoDream.ts', 'FIXED: cli_utils.py - Auto dream service'),
    (r'src\services\compact\compact.ts', 'FIXED: compact_service.py - Compact service'),
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