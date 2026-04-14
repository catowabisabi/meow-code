import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\commands\advisor.ts', 'FIXED: commands.py - AdvisorCommand'),
    (r'src\commands\bridge-kick.ts', 'FIXED: enhanced_bridge.py - BridgeKickCommand'),
    (r'src\commands\brief.ts', 'FIXED: brief.py - BriefCommand'),
    (r'src\commands\commit-push-pr.ts', 'FIXED: commands.py - CommitPushPRCommand'),
    (r'src\commands\commit.ts', 'FIXED: commands.py - CommitCommand'),
    (r'src\commands\createMovedToPluginCommand.ts', 'FIXED: plugin_system.py - CreateMovedToPluginCommand'),
    (r'src\commands\init-verifiers.ts', 'FIXED: commands.py - InitVerifiersCommand'),
    (r'src\commands\init.ts', 'FIXED: commands.py - InitCommand'),
    (r'src\commands\insights.ts', 'FIXED: analytics.py - InsightsCommand'),
    (r'src\commands\review.ts', 'FIXED: review_tools.py - ReviewCommand'),
    (r'src\commands\security-review.ts', 'FIXED: review_tools.py - SecurityReviewCommand'),
    (r'src\commands\version.ts', 'FIXED: cli_utils.py - VersionCommand'),
    (r'src\types\command.ts', 'FIXED: commands.py - Command types'),
    (r'src\utils\commandLifecycle.ts', 'FIXED: commands.py - CommandLifecycle'),
    (r'src\utils\exampleCommands.ts', 'FIXED: commands.py - ExampleCommands'),
    (r'src\utils\immediateCommand.ts', 'FIXED: commands.py - ImmediateCommand'),
    (r'src\utils\ShellCommand.ts', 'FIXED: bash.py - ShellCommand'),
    (r'src\utils\slashCommandParsing.ts', 'FIXED: commands.py - SlashCommandParsing'),
    (r'src\utils\bash\bashPipeCommand.ts', 'FIXED: bash.py - BashPipeCommand'),
    (r'src\utils\bash\commands.ts', 'FIXED: bash.py - BashCommands'),
    (r'src\utils\bash\ParsedCommand.ts', 'FIXED: bash.py - ParsedCommand'),
    (r'src\utils\plugins\loadPluginCommands.ts', 'FIXED: plugin_system.py - LoadPluginCommands'),
    (r'src\utils\shell\readOnlyCommandValidation.ts', 'FIXED: shell_permissions.py - ReadOnlyCommandValidation'),
    (r'src\utils\suggestions\commandSuggestions.ts', 'FIXED: hooks_system.py - CommandSuggestions'),
    (r'src\tools\BashTool\bashCommandHelpers.ts', 'FIXED: bash.py - BashCommandHelpers'),
    (r'src\tools\BashTool\commandSemantics.ts', 'FIXED: command_semantics.py - CommandSemantics'),
    (r'src\tools\BashTool\destructiveCommandWarning.ts', 'FIXED: destructive_command_warning.py - DestructiveCommandWarning'),
    (r'src\tools\BashTool\types.ts', 'FIXED: bash.py - BashTool types'),
    (r'src\tools\BashTool\shellCommandKind.ts', 'FIXED: bash.py - ShellCommandKind'),
    (r'src\tools\BashTool\constants.ts', 'FIXED: bash.py - BashTool constants'),
    (r'src\tools\BashTool\index.ts', 'FIXED: bash.py - BashTool index'),
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