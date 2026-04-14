import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\hooks\renderPlaceholder.ts', 'FIXED: cli_utils.py - RenderPlaceholder'),
    (r'src\commands.ts', 'FIXED: commands.py - Commands'),
    (r'src\context.ts', 'FIXED: cli_utils.py - Context'),
    (r'src\cost-tracker.ts', 'FIXED: analytics.py - CostTracker'),
    (r'src\costHook.ts', 'FIXED: analytics.py - CostHook'),
    (r'src\history.ts', 'FIXED: shell.py - History'),
    (r'src\ink.ts', 'FIXED: cli_utils.py - Ink (React)'),
    (r'src\projectOnboardingState.ts', 'FIXED: cli_utils.py - ProjectOnboardingState'),
    (r'src\query.ts', 'FIXED: query_engine.py - QueryEngine'),
    (r'src\setup.ts', 'FIXED: commands.py - SetupCommand'),
    (r'src\Task.ts', 'FIXED: task_tools.py - Task'),
    (r'src\tools.ts', 'FIXED: enhanced_types.py - Tools'),
    (r'src\tools\BashTool\BashTool.tsx', 'FIXED: bash.py - BashTool'),
    (r'src\tools\BashTool\index.ts', 'FIXED: bash.py - BashTool index'),
    (r'src\tools\BashTool\permissions.ts', 'FIXED: shell_permissions.py - BashTool permissions'),
    (r'src\tools\BashTool\prompt.ts', 'FIXED: bash.py - BashTool prompt'),
    (r'src\tools\BashTool\spec.ts', 'FIXED: bash.py - BashTool spec'),
    (r'src\tools\BashTool\types.ts', 'FIXED: bash.py - BashTool types'),
    (r'src\tools\GrepTool\GrepTool.tsx', 'FIXED: grep.py - GrepTool'),
    (r'src\tools\GrepTool\index.ts', 'FIXED: grep.py - GrepTool index'),
    (r'src\tools\GrepTool\permissions.ts', 'FIXED: shell_permissions.py - GrepTool permissions'),
    (r'src\tools\GrepTool\prompt.ts', 'FIXED: grep.py - GrepTool prompt'),
    (r'src\tools\GrepTool\spec.ts', 'FIXED: grep.py - GrepTool spec'),
    (r'src\tools\GrepTool\types.ts', 'FIXED: grep.py - GrepTool types'),
    (r'src\tools\WebFetchTool\WebFetchTool.tsx', 'FIXED: webfetch_tool.py - WebFetchTool'),
    (r'src\tools\WebFetchTool\index.ts', 'FIXED: webfetch_tool.py - WebFetchTool index'),
    (r'src\tools\WebFetchTool\permissions.ts', 'FIXED: shell_permissions.py - WebFetchTool permissions'),
    (r'src\tools\WebFetchTool\prompt.ts', 'FIXED: webfetch_tool.py - WebFetchTool prompt'),
    (r'src\tools\WebFetchTool\spec.ts', 'FIXED: webfetch_tool.py - WebFetchTool spec'),
    (r'src\tools\WebFetchTool\types.ts', 'FIXED: webfetch_tool.py - WebFetchTool types'),
    (r'src\tools\WebSearchTool\WebSearchTool.tsx', 'FIXED: web_search.py - WebSearchTool'),
    (r'src\tools\WebSearchTool\index.ts', 'FIXED: web_search.py - WebSearchTool index'),
    (r'src\tools\WebSearchTool\permissions.ts', 'FIXED: shell_permissions.py - WebSearchTool permissions'),
    (r'src\tools\WebSearchTool\prompt.ts', 'FIXED: web_search.py - WebSearchTool prompt'),
    (r'src\tools\WebSearchTool\spec.ts', 'FIXED: web_search.py - WebSearchTool spec'),
    (r'src\tools\WebSearchTool\types.ts', 'FIXED: web_search.py - WebSearchTool types'),
    (r'src\tools\NotebookEditTool\NotebookEditTool.tsx', 'FIXED: notebook_edit_tool.py - NotebookEditTool'),
    (r'src\tools\NotebookEditTool\index.ts', 'FIXED: notebook_edit_tool.py - NotebookEditTool index'),
    (r'src\tools\NotebookEditTool\permissions.ts', 'FIXED: shell_permissions.py - NotebookEditTool permissions'),
    (r'src\tools\NotebookEditTool\prompt.ts', 'FIXED: notebook_edit_tool.py - NotebookEditTool prompt'),
    (r'src\tools\NotebookEditTool\spec.ts', 'FIXED: notebook_edit_tool.py - NotebookEditTool spec'),
    (r'src\tools\NotebookEditTool\types.ts', 'FIXED: notebook_edit_tool.py - NotebookEditTool types'),
    (r'src\tools\TaskTool\TaskTool.tsx', 'FIXED: task_tools.py - TaskTool'),
    (r'src\tools\TaskTool\index.ts', 'FIXED: task_tools.py - TaskTool index'),
    (r'src\tools\TaskTool\permissions.ts', 'FIXED: shell_permissions.py - TaskTool permissions'),
    (r'src\tools\TaskTool\prompt.ts', 'FIXED: task_tools.py - TaskTool prompt'),
    (r'src\tools\TaskTool\spec.ts', 'FIXED: task_tools.py - TaskTool spec'),
    (r'src\tools\TaskTool\types.ts', 'FIXED: task_tools.py - TaskTool types'),
    (r'src\tools\GlobTool\GlobTool.tsx', 'FIXED: glob_tool.py - GlobTool'),
    (r'src\tools\GlobTool\index.ts', 'FIXED: glob_tool.py - GlobTool index'),
    (r'src\tools\GlobTool\permissions.ts', 'FIXED: shell_permissions.py - GlobTool permissions'),
    (r'src\tools\GlobTool\prompt.ts', 'FIXED: glob_tool.py - GlobTool prompt'),
    (r'src\tools\GlobTool\spec.ts', 'FIXED: glob_tool.py - GlobTool spec'),
    (r'src\tools\GlobTool\types.ts', 'FIXED: glob_tool.py - GlobTool types'),
    (r'src\tools\ReadTool\ReadTool.tsx', 'FIXED: file_tools.py - ReadTool'),
    (r'src\tools\ReadTool\index.ts', 'FIXED: file_tools.py - ReadTool index'),
    (r'src\tools\ReadTool\permissions.ts', 'FIXED: shell_permissions.py - ReadTool permissions'),
    (r'src\tools\ReadTool\prompt.ts', 'FIXED: file_tools.py - ReadTool prompt'),
    (r'src\tools\ReadTool\spec.ts', 'FIXED: file_tools.py - ReadTool spec'),
    (r'src\tools\ReadTool\types.ts', 'FIXED: file_tools.py - ReadTool types'),
    (r'src\tools\WriteTool\WriteTool.tsx', 'FIXED: file_tools.py - WriteTool'),
    (r'src\tools\WriteTool\index.ts', 'FIXED: file_tools.py - WriteTool index'),
    (r'src\tools\WriteTool\permissions.ts', 'FIXED: shell_permissions.py - WriteTool permissions'),
    (r'src\tools\WriteTool\prompt.ts', 'FIXED: file_tools.py - WriteTool prompt'),
    (r'src\tools\WriteTool\spec.ts', 'FIXED: file_tools.py - WriteTool spec'),
    (r'src\tools\WriteTool\types.ts', 'FIXED: file_tools.py - WriteTool types'),
    (r'src\tools\EditTool\EditTool.tsx', 'FIXED: file_tools.py - EditTool'),
    (r'src\tools\EditTool\index.ts', 'FIXED: file_tools.py - EditTool index'),
    (r'src\tools\EditTool\permissions.ts', 'FIXED: shell_permissions.py - EditTool permissions'),
    (r'src\tools\EditTool\prompt.ts', 'FIXED: file_tools.py - EditTool prompt'),
    (r'src\tools\EditTool\spec.ts', 'FIXED: file_tools.py - EditTool spec'),
    (r'src\tools\EditTool\types.ts', 'FIXED: file_tools.py - EditTool types'),
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