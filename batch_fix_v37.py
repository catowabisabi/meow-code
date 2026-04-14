import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\tools\FileEditTool\constants.ts', 'FIXED: file_tools.py - FileEditTool constants'),
    (r'src\tools\FileEditTool\FileEditTool.ts', 'FIXED: file_tools.py - FileEditTool'),
    (r'src\tools\FileEditTool\prompt.ts', 'FIXED: file_tools.py - FileEditTool prompt'),
    (r'src\tools\FileEditTool\types.ts', 'FIXED: file_tools.py - FileEditTool types'),
    (r'src\tools\FileEditTool\utils.ts', 'FIXED: file_tools.py - FileEditTool utils'),
    (r'src\tools\FileReadTool\prompt.ts', 'FIXED: file_tools.py - FileReadTool prompt'),
    (r'src\tools\FileWriteTool\FileWriteTool.ts', 'FIXED: file_tools.py - FileWriteTool'),
    (r'src\tools\FileWriteTool\prompt.ts', 'FIXED: file_tools.py - FileWriteTool prompt'),
    (r'src\tools\ListMcpResourcesTool\ListMcpResourcesTool.ts', 'FIXED: list_mcp_resources_tool.py - ListMcpResourcesTool'),
    (r'src\tools\ListMcpResourcesTool\prompt.ts', 'FIXED: list_mcp_resources_tool.py - ListMcpResourcesTool prompt'),
    (r'src\tools\LSPTool\formatters.ts', 'FIXED: lsp_tool.py - LSPTool formatters'),
    (r'src\tools\LSPTool\prompt.ts', 'FIXED: lsp_tool.py - LSPTool prompt'),
    (r'src\tools\LSPTool\schemas.ts', 'FIXED: lsp_tool.py - LSPTool schemas'),
    (r'src\tools\LSPTool\symbolContext.ts', 'FIXED: lsp_tool.py - LSPTool symbol context'),
    (r'src\tools\McpAuthTool\McpAuthTool.ts', 'FIXED: mcp_tools.py - McpAuthTool'),
    (r'src\tools\MCPTool\classifyForCollapse.ts', 'FIXED: mcp_tools.py - MCP classify for collapse'),
    (r'src\tools\NotebookEditTool\constants.ts', 'FIXED: notebook_edit_tool.py - NotebookEditTool constants'),
    (r'src\tools\NotebookEditTool\NotebookEditTool.ts', 'FIXED: notebook_edit_tool.py - NotebookEditTool'),
    (r'src\tools\PowerShellTool\clmTypes.ts', 'FIXED: powershell/types.py - PowerShell CLM types'),
    (r'src\tools\PowerShellTool\commandSemantics.ts', 'FIXED: powershell/semantics.py - PowerShell command semantics'),
    (r'src\tools\PowerShellTool\commonParameters.ts', 'FIXED: powershell/canonical.py - PowerShell common parameters'),
    (r'src\tools\PowerShellTool\destructiveCommandWarning.ts', 'FIXED: destructive_command_warning.py - PowerShell destructive warning'),
    (r'src\tools\PowerShellTool\gitSafety.ts', 'FIXED: powershell/execute.py - PowerShell git safety'),
    (r'src\tools\PowerShellTool\modeValidation.ts', 'FIXED: powershell/execute.py - PowerShell mode validation'),
    (r'src\tools\PowerShellTool\pathValidation.ts', 'FIXED: path_validation.py - PowerShell path validation'),
    (r'src\tools\PowerShellTool\powershellPermissions.ts', 'FIXED: powershell/permissions.py - PowerShell permissions'),
    (r'src\tools\PowerShellTool\powershellSecurity.ts', 'FIXED: powershell_security.py - PowerShell security'),
    (r'src\tools\PowerShellTool\prompt.ts', 'FIXED: powershell_tool.py - PowerShellTool prompt'),
    (r'src\tools\PowerShellTool\readOnlyValidation.ts', 'FIXED: read_only_validation.py - PowerShell read-only validation'),
    (r'src\tools\PowerShellTool\toolName.ts', 'FIXED: powershell_tool.py - PowerShellTool name'),
    (r'src\tools\ReadMcpResourceTool\prompt.ts', 'FIXED: read_mcp_resource_tool.py - ReadMcpResourceTool prompt'),
    (r'src\tools\ReadMcpResourceTool\ReadMcpResourceTool.ts', 'FIXED: read_mcp_resource_tool.py - ReadMcpResourceTool'),
    (r'src\tools\RemoteTriggerTool\RemoteTriggerTool.ts', 'FIXED: remote_trigger_tool.py - RemoteTriggerTool'),
    (r'src\tools\REPLTool\constants.ts', 'FIXED: repl.py - REPLTool constants'),
    (r'src\tools\REPLTool\primitiveTools.ts', 'FIXED: repl.py - REPLTool primitive tools'),
    (r'src\tools\ScheduleCronTool\CronCreateTool.ts', 'FIXED: schedule_cron_tool.py - CronCreateTool'),
    (r'src\tools\ScheduleCronTool\CronDeleteTool.ts', 'FIXED: schedule_cron_tool.py - CronDeleteTool'),
    (r'src\tools\ScheduleCronTool\CronListTool.ts', 'FIXED: schedule_cron_tool.py - CronListTool'),
    (r'src\tools\SendMessageTool\constants.ts', 'FIXED: send_message_tool.py - SendMessageTool constants'),
    (r'src\tools\SendMessageTool\SendMessageTool.ts', 'FIXED: send_message_tool.py - SendMessageTool'),
    (r'src\tools\shared\gitOperationTracking.ts', 'FIXED: git_fs.py - Git operation tracking'),
    (r'src\tools\shared\spawnMultiAgent.ts', 'FIXED: remote_swarm.py - Spawn multi-agent'),
    (r'src\tools\SkillTool\constants.ts', 'FIXED: skill_tool.py - SkillTool constants'),
    (r'src\tools\SyntheticOutputTool\SyntheticOutputTool.ts', 'FIXED: synthetic_output_tool.py - SyntheticOutputTool'),
    (r'src\tools\TaskCreateTool\constants.ts', 'FIXED: task_create.py - TaskCreateTool constants'),
    (r'src\tools\TaskGetTool\constants.ts', 'FIXED: task_get.py - TaskGetTool constants'),
    (r'src\tools\TaskGetTool\TaskGetTool.ts', 'FIXED: task_get.py - TaskGetTool'),
    (r'src\tools\TaskListTool\constants.ts', 'FIXED: task_list.py - TaskListTool constants'),
    (r'src\tools\TaskListTool\TaskListTool.ts', 'FIXED: task_list.py - TaskListTool'),
    (r'src\tools\TaskOutputTool\constants.ts', 'FIXED: task_output.py - TaskOutputTool constants'),
]

updated = 0
for path, fix in fixes:
    c.execute('UPDATE files SET notes = ? WHERE src_path = ?', (fix, path))
    if c.rowcount > 0:
        updated += 1

conn.commit()
print(f'Updated {updated} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()