import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\tools\ExitWorktreeTool\ExitWorktreeTool.ts', 'FIXED: worktree_tools.py - ExitWorktreeTool'),
    (r'src\tools\ExitWorktreeTool\index.ts', 'FIXED: worktree_tools.py - ExitWorktreeTool index'),
    (r'src\tools\ExitWorktreeTool\constants.ts', 'FIXED: worktree_tools.py - ExitWorktreeTool constants'),
    (r'src\tools\ExitWorktreeTool\permissions.ts', 'FIXED: shell_permissions.py - ExitWorktreeTool permissions'),
    (r'src\tools\ExitWorktreeTool\prompt.ts', 'FIXED: worktree_tools.py - ExitWorktreeTool prompt'),
    (r'src\tools\ExitWorktreeTool\spec.ts', 'FIXED: worktree_tools.py - ExitWorktreeTool spec'),
    (r'src\tools\ExitWorktreeTool\types.ts', 'FIXED: worktree_tools.py - ExitWorktreeTool types'),
    (r'src\tools\ExitPlanModeTool\ExitPlanModeTool.ts', 'FIXED: plan_mode_tools.py - ExitPlanModeTool'),
    (r'src\tools\ExitPlanModeTool\index.ts', 'FIXED: plan_mode_tools.py - ExitPlanModeTool index'),
    (r'src\tools\ExitPlanModeTool\constants.ts', 'FIXED: plan_mode_tools.py - ExitPlanModeTool constants'),
    (r'src\tools\ExitPlanModeTool\permissions.ts', 'FIXED: shell_permissions.py - ExitPlanModeTool permissions'),
    (r'src\tools\ExitPlanModeTool\prompt.ts', 'FIXED: plan_mode_tools.py - ExitPlanModeTool prompt'),
    (r'src\tools\ExitPlanModeTool\spec.ts', 'FIXED: plan_mode_tools.py - ExitPlanModeTool spec'),
    (r'src\tools\ExitPlanModeTool\types.ts', 'FIXED: plan_mode_tools.py - ExitPlanModeTool types'),
    (r'src\tools\TodoWriteTool\TodoWriteTool.tsx', 'FIXED: todo_write.py - TodoWriteTool'),
    (r'src\tools\TodoWriteTool\index.ts', 'FIXED: todo_write.py - TodoWriteTool index'),
    (r'src\tools\TodoWriteTool\permissions.ts', 'FIXED: shell_permissions.py - TodoWriteTool permissions'),
    (r'src\tools\TodoWriteTool\prompt.ts', 'FIXED: todo_write.py - TodoWriteTool prompt'),
    (r'src\tools\TodoWriteTool\spec.ts', 'FIXED: todo_write.py - TodoWriteTool spec'),
    (r'src\tools\TodoWriteTool\types.ts', 'FIXED: todo_write.py - TodoWriteTool types'),
    (r'src\tools\TaskCreateTool\TaskCreateTool.tsx', 'FIXED: task_create.py - TaskCreateTool'),
    (r'src\tools\TaskCreateTool\index.ts', 'FIXED: task_create.py - TaskCreateTool index'),
    (r'src\tools\TaskCreateTool\permissions.ts', 'FIXED: shell_permissions.py - TaskCreateTool permissions'),
    (r'src\tools\TaskCreateTool\prompt.ts', 'FIXED: task_create.py - TaskCreateTool prompt'),
    (r'src\tools\TaskCreateTool\spec.ts', 'FIXED: task_create.py - TaskCreateTool spec'),
    (r'src\tools\TaskCreateTool\types.ts', 'FIXED: task_create.py - TaskCreateTool types'),
    (r'src\tools\TaskGetTool\TaskGetTool.tsx', 'FIXED: task_get.py - TaskGetTool'),
    (r'src\tools\TaskGetTool\index.ts', 'FIXED: task_get.py - TaskGetTool index'),
    (r'src\tools\TaskGetTool\permissions.ts', 'FIXED: shell_permissions.py - TaskGetTool permissions'),
    (r'src\tools\TaskGetTool\prompt.ts', 'FIXED: task_get.py - TaskGetTool prompt'),
    (r'src\tools\TaskGetTool\spec.ts', 'FIXED: task_get.py - TaskGetTool spec'),
    (r'src\tools\TaskGetTool\types.ts', 'FIXED: task_get.py - TaskGetTool types'),
    (r'src\tools\TaskListTool\TaskListTool.tsx', 'FIXED: task_list.py - TaskListTool'),
    (r'src\tools\TaskListTool\index.ts', 'FIXED: task_list.py - TaskListTool index'),
    (r'src\tools\TaskListTool\permissions.ts', 'FIXED: shell_permissions.py - TaskListTool permissions'),
    (r'src\tools\TaskListTool\prompt.ts', 'FIXED: task_list.py - TaskListTool prompt'),
    (r'src\tools\TaskListTool\spec.ts', 'FIXED: task_list.py - TaskListTool spec'),
    (r'src\tools\TaskListTool\types.ts', 'FIXED: task_list.py - TaskListTool types'),
    (r'src\tools\TaskOutputTool\TaskOutputTool.tsx', 'FIXED: task_output.py - TaskOutputTool'),
    (r'src\tools\TaskOutputTool\index.ts', 'FIXED: task_output.py - TaskOutputTool index'),
    (r'src\tools\TaskOutputTool\permissions.ts', 'FIXED: shell_permissions.py - TaskOutputTool permissions'),
    (r'src\tools\TaskOutputTool\prompt.ts', 'FIXED: task_output.py - TaskOutputTool prompt'),
    (r'src\tools\TaskOutputTool\spec.ts', 'FIXED: task_output.py - TaskOutputTool spec'),
    (r'src\tools\TaskOutputTool\types.ts', 'FIXED: task_output.py - TaskOutputTool types'),
    (r'src\tools\TaskStopTool\TaskStopTool.tsx', 'FIXED: task_stop.py - TaskStopTool'),
    (r'src\tools\TaskStopTool\index.ts', 'FIXED: task_stop.py - TaskStopTool index'),
    (r'src\tools\TaskStopTool\permissions.ts', 'FIXED: shell_permissions.py - TaskStopTool permissions'),
    (r'src\tools\TaskStopTool\prompt.ts', 'FIXED: task_stop.py - TaskStopTool prompt'),
    (r'src\tools\TaskStopTool\spec.ts', 'FIXED: task_stop.py - TaskStopTool spec'),
    (r'src\tools\TaskStopTool\types.ts', 'FIXED: task_stop.py - TaskStopTool types'),
    (r'src\tools\TaskUpdateTool\TaskUpdateTool.tsx', 'FIXED: task_update.py - TaskUpdateTool'),
    (r'src\tools\TaskUpdateTool\index.ts', 'FIXED: task_update.py - TaskUpdateTool index'),
    (r'src\tools\TaskUpdateTool\permissions.ts', 'FIXED: shell_permissions.py - TaskUpdateTool permissions'),
    (r'src\tools\TaskUpdateTool\prompt.ts', 'FIXED: task_update.py - TaskUpdateTool prompt'),
    (r'src\tools\TaskUpdateTool\spec.ts', 'FIXED: task_update.py - TaskUpdateTool spec'),
    (r'src\tools\TaskUpdateTool\types.ts', 'FIXED: task_update.py - TaskUpdateTool types'),
    (r'src\tools\MCPTool\MCPTool.tsx', 'FIXED: mcp_tools.py - MCPTool'),
    (r'src\tools\MCPTool\index.ts', 'FIXED: mcp_tools.py - MCPTool index'),
    (r'src\tools\MCPTool\permissions.ts', 'FIXED: shell_permissions.py - MCPTool permissions'),
    (r'src\tools\MCPTool\prompt.ts', 'FIXED: mcp_tools.py - MCPTool prompt'),
    (r'src\tools\MCPTool\spec.ts', 'FIXED: mcp_tools.py - MCPTool spec'),
    (r'src\tools\MCPTool\types.ts', 'FIXED: mcp_tools.py - MCPTool types'),
    (r'src\tools\LspTool\LspTool.tsx', 'FIXED: lsp_tool.py - LspTool'),
    (r'src\tools\LspTool\index.ts', 'FIXED: lsp_tool.py - LspTool index'),
    (r'src\tools\LspTool\permissions.ts', 'FIXED: shell_permissions.py - LspTool permissions'),
    (r'src\tools\LspTool\prompt.ts', 'FIXED: lsp_tool.py - LspTool prompt'),
    (r'src\tools\LspTool\spec.ts', 'FIXED: lsp_tool.py - LspTool spec'),
    (r'src\tools\LspTool\types.ts', 'FIXED: lsp_tool.py - LspTool types'),
    (r'src\tools\MemoryTool\MemoryTool.tsx', 'FIXED: memory_tools.py - MemoryTool'),
    (r'src\tools\MemoryTool\index.ts', 'FIXED: memory_tools.py - MemoryTool index'),
    (r'src\tools\MemoryTool\permissions.ts', 'FIXED: shell_permissions.py - MemoryTool permissions'),
    (r'src\tools\MemoryTool\prompt.ts', 'FIXED: memory_tools.py - MemoryTool prompt'),
    (r'src\tools\MemoryTool\spec.ts', 'FIXED: memory_tools.py - MemoryTool spec'),
    (r'src\tools\MemoryTool\types.ts', 'FIXED: memory_tools.py - MemoryTool types'),
    (r'src\tools\NotionTool\NotionTool.tsx', 'FIXED: notion_tools.py - NotionTool'),
    (r'src\tools\NotionTool\index.ts', 'FIXED: notion_tools.py - NotionTool index'),
    (r'src\tools\NotionTool\permissions.ts', 'FIXED: shell_permissions.py - NotionTool permissions'),
    (r'src\tools\NotionTool\prompt.ts', 'FIXED: notion_tools.py - NotionTool prompt'),
    (r'src\tools\NotionTool\spec.ts', 'FIXED: notion_tools.py - NotionTool spec'),
    (r'src\tools\NotionTool\types.ts', 'FIXED: notion_tools.py - NotionTool types'),
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