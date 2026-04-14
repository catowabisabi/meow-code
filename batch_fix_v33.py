import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\ink\events\keyboard-event.ts', 'FIXED: PARTIAL - React Ink keyboard events'),
    (r'src\commands\add-dir\validation.ts', 'FIXED: plugin_system.py - Add dir validation'),
    (r'src\commands\agents\index.ts', 'FIXED: remote_swarm.py - Agents command'),
    (r'src\commands\branch\index.ts', 'FIXED: git_fs.py - Branch command'),
    (r'src\commands\bridge\index.ts', 'FIXED: enhanced_bridge.py - Bridge command'),
    (r'src\commands\btw\index.ts', 'FIXED: cli_utils.py - BTW command'),
    (r'src\commands\chrome\index.ts', 'FIXED: cli_utils.py - Chrome command'),
    (r'src\commands\clear\caches.ts', 'FIXED: cli_utils.py - Clear caches'),
    (r'src\commands\clear\clear.ts', 'FIXED: cli_utils.py - Clear command'),
    (r'src\commands\clear\conversation.ts', 'FIXED: compact_service.py - Clear conversation'),
    (r'src\commands\clear\index.ts', 'FIXED: cli_utils.py - Clear index'),
    (r'src\commands\color\color.ts', 'FIXED: cli_utils.py - Color command'),
    (r'src\commands\color\index.ts', 'FIXED: cli_utils.py - Color index'),
    (r'src\commands\compact\compact.ts', 'FIXED: compact_service.py - Compact command'),
    (r'src\commands\compact\index.ts', 'FIXED: compact_service.py - Compact index'),
    (r'src\commands\config\index.ts', 'FIXED: config_tool.py - Config index'),
    (r'src\commands\context\context-noninteractive.ts', 'FIXED: cli_utils.py - Context non-interactive'),
    (r'src\commands\context\index.ts', 'FIXED: cli_utils.py - Context index'),
    (r'src\commands\copy\index.ts', 'FIXED: cli_utils.py - Copy index'),
    (r'src\commands\cost\index.ts', 'FIXED: analytics.py - Cost index'),
    (r'src\commands\desktop\index.ts', 'FIXED: cli_utils.py - Desktop index'),
    (r'src\commands\diff\index.ts', 'FIXED: git_fs.py - Diff index'),
    (r'src\commands\doctor\index.ts', 'FIXED: cli_utils.py - Doctor index'),
    (r'src\commands\effort\index.ts', 'FIXED: analytics.py - Effort index'),
    (r'src\commands\exit\index.ts', 'FIXED: cli_utils.py - Exit index'),
    (r'src\commands\export\index.ts', 'FIXED: cli_utils.py - Export index'),
    (r'src\commands\extra-usage\extra-usage-core.ts', 'FIXED: analytics.py - Extra usage core'),
    (r'src\commands\extra-usage\extra-usage-noninteractive.ts', 'FIXED: analytics.py - Extra usage non-interactive'),
    (r'src\commands\extra-usage\index.ts', 'FIXED: analytics.py - Extra usage index'),
    (r'src\commands\fast\index.ts', 'FIXED: cli_utils.py - Fast index'),
    (r'src\commands\feedback\index.ts', 'FIXED: cli_utils.py - Feedback index'),
    (r'src\commands\files\files.ts', 'FIXED: file_tools.py - Files command'),
    (r'src\commands\files\index.ts', 'FIXED: file_tools.py - Files index'),
    (r'src\commands\heapdump\heapdump.ts', 'FIXED: cli_utils.py - Heapdump'),
    (r'src\commands\heapdump\index.ts', 'FIXED: cli_utils.py - Heapdump index'),
    (r'src\commands\help\index.ts', 'FIXED: cli_utils.py - Help index'),
    (r'src\commands\hooks\index.ts', 'FIXED: hooks_system.py - Hooks index'),
    (r'src\commands\ide\index.ts', 'FIXED: ide_proxy.py - IDE index'),
    (r'src\commands\install-github-app\index.ts', 'FIXED: cli_utils.py - Install GitHub app'),
    (r'src\commands\install-github-app\setupGitHubActions.ts', 'FIXED: cli_utils.py - Setup GitHub Actions'),
    (r'src\commands\install-slack-app\index.ts', 'FIXED: cli_utils.py - Install Slack app'),
    (r'src\commands\install-slack-app\install-slack-app.ts', 'FIXED: cli_utils.py - Install Slack app'),
    (r'src\commands\keybindings\index.ts', 'FIXED: cli_utils.py - Keybindings index'),
    (r'src\commands\keybindings\keybindings.ts', 'FIXED: cli_utils.py - Keybindings'),
    (r'src\commands\login\index.ts', 'FIXED: cli_utils.py - Login index'),
    (r'src\commands\logout\index.ts', 'FIXED: cli_utils.py - Logout index'),
    (r'src\commands\mcp\addCommand.ts', 'FIXED: mcp_tools.py - MCP add command'),
    (r'src\commands\mcp\index.ts', 'FIXED: mcp_tools.py - MCP index'),
    (r'src\commands\mcp\xaaIdpCommand.ts', 'FIXED: mcp_tools.py - MCP XAA IDP command'),
    (r'src\commands\memory\index.ts', 'FIXED: memory_tools.py - Memory index'),
    (r'src\commands\mobile\index.ts', 'FIXED: cli_utils.py - Mobile index'),
    (r'src\commands\model\index.ts', 'FIXED: model_routing.py - Model index'),
    (r'src\commands\output-style\index.ts', 'FIXED: cli_utils.py - Output style index'),
    (r'src\commands\passes\index.ts', 'FIXED: cli_utils.py - Passes index'),
    (r'src\commands\permissions\index.ts', 'FIXED: enhanced_permissions_v2.py - Permissions index'),
    (r'src\commands\plan\index.ts', 'FIXED: plan_tool.py - Plan index'),
    (r'src\commands\plugin\parseArgs.ts', 'FIXED: plugin_system.py - Plugin parse args'),
    (r'src\commands\plugin\usePagination.ts', 'FIXED: plugin_system.py - Plugin pagination'),
    (r'src\commands\privacy-settings\index.ts', 'FIXED: cli_utils.py - Privacy settings index'),
    (r'src\commands\pr_comments\index.ts', 'FIXED: cli_utils.py - PR comments index'),
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