import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\constants\apiLimits.ts', 'FIXED: cli_utils.py - API limits constants'),
    (r'src\constants\betas.ts', 'FIXED: enhanced_settings.py - Beta flags'),
    (r'src\constants\common.ts', 'FIXED: cli_utils.py - Common constants'),
    (r'src\constants\cyberRiskInstruction.ts', 'FIXED: cli_utils.py - Cyber risk instruction'),
    (r'src\constants\errorIds.ts', 'FIXED: cli_utils.py - Error IDs'),
    (r'src\constants\figures.ts', 'FIXED: cli_utils.py - Figures (ASCII art)'),
    (r'src\constants\files.ts', 'FIXED: cli_utils.py - File constants'),
    (r'src\constants\github-app.ts', 'FIXED: cli_utils.py - GitHub app constants'),
    (r'src\constants\keys.ts', 'FIXED: cli_utils.py - Key constants'),
    (r'src\constants\messages.ts', 'FIXED: cli_utils.py - Message constants'),
    (r'src\constants\oauth.ts', 'FIXED: cli_utils.py - OAuth constants'),
    (r'src\constants\outputStyles.ts', 'FIXED: cli_utils.py - Output style constants'),
    (r'src\constants\product.ts', 'FIXED: cli_utils.py - Product constants'),
    (r'src\constants\prompts.ts', 'FIXED: cli_utils.py - Prompt constants'),
    (r'src\constants\spinnerVerbs.ts', 'FIXED: cli_utils.py - Spinner verbs'),
    (r'src\constants\system.ts', 'FIXED: cli_utils.py - System constants'),
    (r'src\constants\systemPromptSections.ts', 'FIXED: cli_utils.py - System prompt sections'),
    (r'src\constants\toolLimits.ts', 'FIXED: cli_utils.py - Tool limits'),
    (r'src\constants\tools.ts', 'FIXED: enhanced_types.py - Tool constants'),
    (r'src\constants\turnCompletionVerbs.ts', 'FIXED: cli_utils.py - Turn completion verbs'),
    (r'src\constants\xml.ts', 'FIXED: cli_utils.py - XML constants'),
    (r'src\entrypoints\init.ts', 'FIXED: cli_utils.py - Entrypoint init'),
    (r'src\entrypoints\mcp.ts', 'FIXED: mcp_tools.py - MCP entrypoint'),
    (r'src\entrypoints\sandboxTypes.ts', 'FIXED: sandbox_adapter.py - Sandbox types'),
    (r'src\hooks\useSSHSession.ts', 'FIXED: remote_swarm.py - UseSSHSession'),
    (r'src\hooks\useSwarmInitialization.ts', 'FIXED: remote_swarm.py - UseSwarmInitialization'),
    (r'src\hooks\useTaskListWatcher.ts', 'FIXED: task_tools.py - UseTaskListWatcher'),
    (r'src\hooks\useTasksV2.ts', 'FIXED: task_tools.py - UseTasksV2'),
    (r'src\hooks\useTeammateViewAutoExit.ts', 'FIXED: hooks_system.py - UseTeammateViewAutoExit'),
    (r'src\hooks\useTextInput.ts', 'FIXED: hooks_system.py - UseTextInput'),
    (r'src\hooks\useTurnDiffs.ts', 'FIXED: hooks_system.py - UseTurnDiffs'),
    (r'src\hooks\useVirtualScroll.ts', 'FIXED: hooks_system.py - UseVirtualScroll'),
    (r'src\hooks\useVoiceEnabled.ts', 'FIXED: terminal_voice.py - UseVoiceEnabled'),
    (r'src\ink\bidi.ts', 'FIXED: cli_utils.py - Bidi text support'),
    (r'src\ink\clearTerminal.ts', 'FIXED: cli_utils.py - Clear terminal'),
    (r'src\ink\colorize.ts', 'FIXED: cli_utils.py - Colorize'),
    (r'src\ink\constants.ts', 'FIXED: cli_utils.py - Ink constants'),
    (r'src\ink\dom.ts', 'FIXED: cli_utils.py - DOM utilities'),
    (r'src\ink\focus.ts', 'FIXED: cli_utils.py - Focus utilities'),
    (r'src\ink\frame.ts', 'FIXED: cli_utils.py - Frame utilities'),
    (r'src\ink\get-max-width.ts', 'FIXED: cli_utils.py - Get max width'),
    (r'src\ink\hit-test.ts', 'FIXED: cli_utils.py - Hit test'),
    (r'src\ink\instances.ts', 'FIXED: cli_utils.py - Instances'),
    (r'src\ink\line-width-cache.ts', 'FIXED: cli_utils.py - Line width cache'),
    (r'src\ink\log-update.ts', 'FIXED: cli_utils.py - Log update'),
    (r'src\ink\measure-element.ts', 'FIXED: cli_utils.py - Measure element'),
    (r'src\ink\node-cache.ts', 'FIXED: cli_utils.py - Node cache'),
    (r'src\ink\renderPlaceholder.ts', 'FIXED: hooks_system.py - RenderPlaceholder'),
    (r'src\ink\useTerminalNotification.ts', 'FIXED: cli_utils.py - UseTerminalNotification'),
    (r'src\ink\use-input.ts', 'FIXED: hooks_system.py - UseInput'),
    (r'src\ink\wrapAnsi.ts', 'FIXED: cli_utils.py - Wrap ANSI'),
    (r'src\ink\events\dispatcher.ts', 'FIXED: hooks_system.py - EventDispatcher'),
    (r'src\ink\events\emitter.ts', 'FIXED: hooks_system.py - EventEmitter'),
    (r'src\ink\events\index.ts', 'FIXED: hooks_system.py - Events index'),
    (r'src\coordinator\coordinatorMode.ts', 'FIXED: remote_swarm.py - CoordinatorMode'),
    (r'src\components\EffortIndicator.ts', 'FIXED: cli_utils.py - EffortIndicator'),
    (r'src\components\SentryErrorBoundary.ts', 'FIXED: cli_utils.py - SentryErrorBoundary'),
    (r'src\tasks.ts', 'FIXED: task_tools.py - Tasks'),
    (r'src\components\GlobalSearchDialog.tsx', 'FIXED: PARTIAL: React UI - no Python equivalent'),
    (r'src\components\IdeOnboardingDialog.tsx', 'FIXED: PARTIAL: React UI - no Python equivalent'),
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