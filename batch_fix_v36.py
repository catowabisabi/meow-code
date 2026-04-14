import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\commands\plugin\BrowseMarketplace.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\DiscoverPlugins.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\index.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\ManageMarketplaces.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\ManagePlugins.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\plugin.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\PluginErrors.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\PluginOptionsDialog.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\PluginOptionsFlow.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\PluginSettings.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\PluginTrustWarning.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\UnifiedInstalledCell.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\ValidatePlugin.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\privacy-settings\privacy-settings.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\rate-limit-options\rate-limit-options.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\remote-env\remote-env.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\remote-setup\remote-setup.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\resume\resume.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\review\ultrareviewCommand.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\review\UltrareviewOverageDialog.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\sandbox-toggle\sandbox-toggle.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\session\session.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\skills\skills.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\stats\stats.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\status\status.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\cli\handlers\mcp.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\cli\handlers\util.tsx', 'FIXED: PARTIAL - React UI component'),
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