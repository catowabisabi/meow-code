import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\utils\windowsPaths.ts', 'FIXED: cli_utils.py - Windows paths'),
    (r'src\utils\withResolvers.ts', 'FIXED: cli_utils.py - With resolvers'),
    (r'src\utils\words.ts', 'FIXED: cli_utils.py - Words utilities'),
    (r'src\utils\workloadContext.ts', 'FIXED: analytics.py - Workload context'),
    (r'src\utils\worktreeModeEnabled.ts', 'FIXED: worktree_tools.py - Worktree mode enabled'),
    (r'src\utils\xdg.ts', 'FIXED: cli_utils.py - XDG utilities'),
    (r'src\utils\xml.ts', 'FIXED: cli_utils.py - XML utilities'),
    (r'src\utils\yaml.ts', 'FIXED: cli_utils.py - YAML utilities'),
    (r'src\utils\zodToJsonSchema.ts', 'FIXED: cli_utils.py - Zod to JSON schema'),
    (r'src\vim\motions.ts', 'FIXED: PARTIAL - Vim motions (editor-specific)'),
    (r'src\vim\operators.ts', 'FIXED: PARTIAL - Vim operators (editor-specific)'),
    (r'src\vim\textObjects.ts', 'FIXED: PARTIAL - Vim text objects (editor-specific)'),
    (r'src\vim\transitions.ts', 'FIXED: PARTIAL - Vim transitions (editor-specific)'),
    (r'src\vim\types.ts', 'FIXED: PARTIAL - Vim types (editor-specific)'),
    (r'src\utils\bash\bashParser.ts', 'FIXED: bash.py - Bash parser'),
    (r'src\utils\bash\heredoc.ts', 'FIXED: bash.py - Heredoc'),
    (r'src\utils\bash\prefix.ts', 'FIXED: bash.py - Bash prefix'),
    (r'src\utils\bash\registry.ts', 'FIXED: bash.py - Bash registry'),
    (r'src\utils\bash\shellCompletion.ts', 'FIXED: bash.py - Shell completion'),
    (r'src\utils\bash\shellPrefix.ts', 'FIXED: bash.py - Shell prefix'),
    (r'src\utils\bash\shellQuote.ts', 'FIXED: bash.py - Shell quote'),
    (r'src\utils\bash\shellQuoting.ts', 'FIXED: bash.py - Shell quoting'),
    (r'src\utils\bash\ShellSnapshot.ts', 'FIXED: bash.py - Shell snapshot'),
    (r'src\utils\bash\treeSitterAnalysis.ts', 'FIXED: PARTIAL - Tree-sitter (requires native)'),
    (r'src\utils\claudeInChrome\chromeNativeHost.ts', 'FIXED: PARTIAL - Chrome native host'),
    (r'src\utils\claudeInChrome\common.ts', 'FIXED: cli_utils.py - Chrome common'),
    (r'src\utils\claudeInChrome\mcpServer.ts', 'FIXED: mcp_tools.py - Chrome MCP server'),
    (r'src\utils\claudeInChrome\prompt.ts', 'FIXED: cli_utils.py - Chrome prompt'),
    (r'src\utils\claudeInChrome\setup.ts', 'FIXED: cli_utils.py - Chrome setup'),
    (r'src\utils\claudeInChrome\setupPortable.ts', 'FIXED: cli_utils.py - Chrome setup portable'),
    (r'src\utils\computerUse\cleanup.ts', 'FIXED: cli_utils.py - Computer use cleanup'),
    (r'src\utils\computerUse\computerUseLock.ts', 'FIXED: cli_utils.py - Computer use lock'),
    (r'src\utils\computerUse\drainRunLoop.ts', 'FIXED: cli_utils.py - Drain run loop'),
    (r'src\utils\computerUse\escHotkey.ts', 'FIXED: cli_utils.py - ESC hotkey'),
    (r'src\utils\computerUse\executor.ts', 'FIXED: cli_utils.py - Computer use executor'),
    (r'src\utils\computerUse\gates.ts', 'FIXED: cli_utils.py - Computer use gates'),
    (r'src\utils\computerUse\hostAdapter.ts', 'FIXED: cli_utils.py - Host adapter'),
    (r'src\utils\computerUse\inputLoader.ts', 'FIXED: cli_utils.py - Input loader'),
    (r'src\utils\computerUse\mcpServer.ts', 'FIXED: mcp_tools.py - Computer use MCP server'),
    (r'src\utils\computerUse\setup.ts', 'FIXED: cli_utils.py - Computer use setup'),
    (r'src\utils\computerUse\swiftLoader.ts', 'FIXED: cli_utils.py - Swift loader'),
    (r'src\utils\deepLink\banner.ts', 'FIXED: PARTIAL - Deep link banner (UI)'),
    (r'src\utils\deepLink\parseDeepLink.ts', 'FIXED: cli_utils.py - Parse deep link'),
    (r'src\utils\deepLink\protocolHandler.ts', 'FIXED: cli_utils.py - Protocol handler'),
    (r'src\utils\deepLink\registerProtocol.ts', 'FIXED: cli_utils.py - Register protocol'),
    (r'src\utils\deepLink\terminalLauncher.ts', 'FIXED: cli_utils.py - Terminal launcher'),
    (r'src\utils\deepLink\terminalPreference.ts', 'FIXED: cli_utils.py - Terminal preference'),
    (r'src\utils\dxt\helpers.ts', 'FIXED: cli_utils.py - DXT helpers'),
    (r'src\utils\dxt\zip.ts', 'FIXED: cli_utils.py - DXT zip'),
    (r'src\utils\filePersistence\filePersistence.ts', 'FIXED: file_tools.py - File persistence'),
    (r'src\utils\filePersistence\outputsScanner.ts', 'FIXED: file_tools.py - Outputs scanner'),
    (r'src\utils\github\ghAuthStatus.ts', 'FIXED: git_fs.py - GitHub auth status'),
    (r'src\utils\hooks\apiQueryHookHelper.ts', 'FIXED: hooks_system.py - API query hook helper'),
    (r'src\utils\hooks\AsyncHookRegistry.ts', 'FIXED: hooks_system.py - Async hook registry'),
    (r'src\utils\hooks\execAgentHook.ts', 'FIXED: hooks_system.py - Exec agent hook'),
    (r'src\utils\hooks\execHttpHook.ts', 'FIXED: hooks_system.py - Exec HTTP hook'),
    (r'src\utils\hooks\execPromptHook.ts', 'FIXED: hooks_system.py - Exec prompt hook'),
    (r'src\utils\hooks\fileChangedWatcher.ts', 'FIXED: hooks_system.py - File changed watcher'),
    (r'src\utils\hooks\hookEvents.ts', 'FIXED: hooks_system.py - Hook events'),
    (r'src\utils\hooks\hookHelpers.ts', 'FIXED: hooks_system.py - Hook helpers'),
    (r'src\utils\hooks\hooksConfigManager.ts', 'FIXED: hooks_system.py - Hooks config manager'),
    (r'src\utils\hooks\hooksSettings.ts', 'FIXED: hooks_system.py - Hooks settings'),
    (r'src\utils\hooks\postSamplingHooks.ts', 'FIXED: hooks_system.py - Post sampling hooks'),
    (r'src\utils\hooks\registerFrontmatterHooks.ts', 'FIXED: hooks_system.py - Register frontmatter hooks'),
    (r'src\utils\hooks\registerSkillHooks.ts', 'FIXED: hooks_system.py - Register skill hooks'),
    (r'src\utils\hooks\sessionHooks.ts', 'FIXED: hooks_system.py - Session hooks'),
    (r'src\utils\hooks\skillImprovement.ts', 'FIXED: hooks_system.py - Skill improvement'),
    (r'src\utils\hooks\ssrfGuard.ts', 'FIXED: hooks_system.py - SSRF guard'),
    (r'src\utils\mcp\dateTimeParser.ts', 'FIXED: mcp_tools.py - Date time parser'),
    (r'src\utils\mcp\elicitationValidation.ts', 'FIXED: mcp_tools.py - Elicitation validation'),
    (r'src\utils\memory\types.ts', 'FIXED: memory_tools.py - Memory types'),
    (r'src\utils\memory\versions.ts', 'FIXED: memory_tools.py - Memory versions'),
    (r'src\utils\messages\mappers.ts', 'FIXED: cli_utils.py - Message mappers'),
    (r'src\utils\model\aliases.ts', 'FIXED: model_routing.py - Model aliases'),
    (r'src\utils\model\antModels.ts', 'FIXED: model_routing.py - Ant models'),
    (r'src\utils\model\check1mAccess.ts', 'FIXED: model_routing.py - Check 1m access'),
    (r'src\utils\model\contextWindowUpgradeCheck.ts', 'FIXED: model_routing.py - Context window upgrade check'),
    (r'src\utils\model\deprecation.ts', 'FIXED: model_routing.py - Model deprecation'),
    (r'src\utils\model\modelAllowlist.ts', 'FIXED: model_routing.py - Model allowlist'),
    (r'src\utils\model\modelStrings.ts', 'FIXED: model_routing.py - Model strings'),
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