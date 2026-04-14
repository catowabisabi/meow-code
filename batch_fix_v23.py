import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\ink\measure-text.ts', 'FIXED: PARTIAL - React Ink terminal rendering'),
    (r'src\ink\optimizer.ts', 'FIXED: PARTIAL - React Ink terminal rendering'),
    (r'src\ink\output.ts', 'FIXED: PARTIAL - React Ink terminal rendering'),
    (r'src\ink\parse-keypress.ts', 'FIXED: PARTIAL - React Ink terminal rendering'),
    (r'src\ink\reconciler.ts', 'FIXED: PARTIAL - React Ink reconciler'),
    (r'src\ink\render-border.ts', 'FIXED: PARTIAL - React Ink border rendering'),
    (r'src\ink\render-node-to-output.ts', 'FIXED: PARTIAL - React Ink node rendering'),
    (r'src\ink\render-to-screen.ts', 'FIXED: PARTIAL - React Ink screen rendering'),
    (r'src\ink\renderer.ts', 'FIXED: PARTIAL - React Ink renderer'),
    (r'src\ink\root.ts', 'FIXED: PARTIAL - React Ink root'),
    (r'src\ink\screen.ts', 'FIXED: PARTIAL - React Ink screen'),
    (r'src\ink\searchHighlight.ts', 'FIXED: PARTIAL - React Ink search highlight'),
    (r'src\ink\selection.ts', 'FIXED: PARTIAL - React Ink selection'),
    (r'src\ink\squash-text-nodes.ts', 'FIXED: PARTIAL - React Ink text node squashing'),
    (r'src\ink\stringWidth.ts', 'FIXED: PARTIAL - React Ink string width'),
    (r'src\ink\styles.ts', 'FIXED: PARTIAL - React Ink styles'),
    (r'src\ink\supports-hyperlinks.ts', 'FIXED: PARTIAL - React Ink hyperlinks'),
    (r'src\ink\tabstops.ts', 'FIXED: PARTIAL - React Ink tabstops'),
    (r'src\ink\terminal-focus-state.ts', 'FIXED: PARTIAL - React Ink terminal focus'),
    (r'src\ink\terminal-querier.ts', 'FIXED: PARTIAL - React Ink terminal querier'),
    (r'src\ink\terminal.ts', 'FIXED: PARTIAL - React Ink terminal'),
    (r'src\ink\termio.ts', 'FIXED: PARTIAL - React Ink termio'),
    (r'src\ink\warn.ts', 'FIXED: PARTIAL - React Ink warning'),
    (r'src\ink\widest-line.ts', 'FIXED: PARTIAL - React Ink widest line'),
    (r'src\ink\wrap-text.ts', 'FIXED: PARTIAL - React Ink wrap text'),
    (r'src\keybindings\defaultBindings.ts', 'FIXED: cli_utils.py - Default keybindings'),
    (r'src\keybindings\loadUserBindings.ts', 'FIXED: cli_utils.py - Load user bindings'),
    (r'src\keybindings\match.ts', 'FIXED: cli_utils.py - Keybinding match'),
    (r'src\keybindings\parser.ts', 'FIXED: cli_utils.py - Keybinding parser'),
    (r'src\keybindings\resolver.ts', 'FIXED: cli_utils.py - Keybinding resolver'),
    (r'src\keybindings\schema.ts', 'FIXED: cli_utils.py - Keybinding schema'),
    (r'src\keybindings\shortcutFormat.ts', 'FIXED: cli_utils.py - Shortcut format'),
    (r'src\keybindings\template.ts', 'FIXED: cli_utils.py - Keybinding template'),
    (r'src\keybindings\useKeybinding.ts', 'FIXED: PARTIAL - React keybinding hook'),
    (r'src\keybindings\useShortcutDisplay.ts', 'FIXED: PARTIAL - React shortcut display'),
    (r'src\keybindings\validate.ts', 'FIXED: cli_utils.py - Keybinding validation'),
    (r'src\memdir\findRelevantMemories.ts', 'FIXED: memory_tools.py - Find relevant memories'),
    (r'src\memdir\memoryAge.ts', 'FIXED: memory_tools.py - Memory age'),
    (r'src\memdir\memoryTypes.ts', 'FIXED: memory_tools.py - Memory types'),
    (r'src\migrations\migrateEnableAllProjectMcpServersToSettings.ts', 'FIXED: enhanced_settings.py - Migration'),
    (r'src\migrations\migrateFennecToOpus.ts', 'FIXED: enhanced_settings.py - Migration'),
    (r'src\migrations\migrateLegacyOpusToCurrent.ts', 'FIXED: enhanced_settings.py - Migration'),
    (r'src\migrations\migrateOpusToOpus1m.ts', 'FIXED: enhanced_settings.py - Migration'),
    (r'src\migrations\migrateReplBridgeEnabledToRemoteControlAtStartup.ts', 'FIXED: enhanced_bridge.py - Migration'),
    (r'src\migrations\migrateSonnet1mToSonnet45.ts', 'FIXED: enhanced_settings.py - Migration'),
    (r'src\migrations\migrateSonnet45ToSonnet46.ts', 'FIXED: enhanced_settings.py - Migration'),
    (r'src\migrations\resetAutoModeOptInForDefaultOffer.ts', 'FIXED: enhanced_settings.py - Migration'),
    (r'src\migrations\resetProToOpusDefault.ts', 'FIXED: enhanced_settings.py - Migration'),
    (r'src\plugins\builtinPlugins.ts', 'FIXED: plugin_system.py - Builtin plugins'),
    (r'src\query\config.ts', 'FIXED: query_engine.py - Query config'),
    (r'src\memdir\memdirIndex.ts', 'FIXED: memory_tools.py - Memory directory index'),
    (r'src\memdir\memdirIndexSearch.ts', 'FIXED: memory_tools.py - Memory directory search'),
    (r'src\memdir\restoreMemories.ts', 'FIXED: memory_tools.py - Restore memories'),
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