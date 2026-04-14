import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\commands\rate-limit-options\index.ts', 'FIXED: model_routing.py - Rate limit options'),
    (r'src\commands\release-notes\index.ts', 'FIXED: cli_utils.py - Release notes index'),
    (r'src\commands\release-notes\release-notes.ts', 'FIXED: cli_utils.py - Release notes'),
    (r'src\commands\reload-plugins\index.ts', 'FIXED: plugin_system.py - Reload plugins index'),
    (r'src\commands\reload-plugins\reload-plugins.ts', 'FIXED: plugin_system.py - Reload plugins'),
    (r'src\commands\remote-env\index.ts', 'FIXED: remote_swarm.py - Remote env index'),
    (r'src\commands\remote-setup\api.ts', 'FIXED: remote_swarm.py - Remote setup API'),
    (r'src\commands\remote-setup\index.ts', 'FIXED: remote_swarm.py - Remote setup index'),
    (r'src\commands\rename\generateSessionName.ts', 'FIXED: enhanced_session.py - Generate session name'),
    (r'src\commands\rename\index.ts', 'FIXED: enhanced_session.py - Rename index'),
    (r'src\commands\rename\rename.ts', 'FIXED: enhanced_session.py - Rename command'),
    (r'src\commands\resume\index.ts', 'FIXED: compact_service.py - Resume index'),
    (r'src\commands\review\reviewRemote.ts', 'FIXED: review_tools.py - Review remote'),
    (r'src\commands\review\ultrareviewEnabled.ts', 'FIXED: review_tools.py - UltraReview enabled'),
    (r'src\commands\rewind\index.ts', 'FIXED: compact_service.py - Rewind index'),
    (r'src\commands\rewind\rewind.ts', 'FIXED: compact_service.py - Rewind command'),
    (r'src\commands\sandbox-toggle\index.ts', 'FIXED: sandbox_adapter.py - Sandbox toggle index'),
    (r'src\commands\session\index.ts', 'FIXED: enhanced_session.py - Session index'),
    (r'src\commands\skills\index.ts', 'FIXED: skill_tool.py - Skills index'),
    (r'src\commands\stats\index.ts', 'FIXED: analytics.py - Stats index'),
    (r'src\commands\status\index.ts', 'FIXED: cli_utils.py - Status index'),
    (r'src\commands\stickers\index.ts', 'FIXED: cli_utils.py - Stickers index'),
    (r'src\commands\stickers\stickers.ts', 'FIXED: cli_utils.py - Stickers'),
    (r'src\commands\thinkback\index.ts', 'FIXED: cli_utils.py - Thinkback index'),
    (r'src\commands\vim\vim.ts', 'FIXED: PARTIAL - Vim command (editor-specific)'),
    (r'src\commands\voice\voice.ts', 'FIXED: terminal_voice.py - Voice command'),
    (r'src\cli\handlers\agents.ts', 'FIXED: remote_swarm.py - Agents handler'),
    (r'src\cli\handlers\auth.ts', 'FIXED: cli_utils.py - Auth handler'),
    (r'src\cli\handlers\autoMode.ts', 'FIXED: cli_utils.py - Auto mode handler'),
    (r'src\cli\transports\ccrClient.ts', 'FIXED: transports.py - CCR client'),
    (r'src\cli\transports\transportUtils.ts', 'FIXED: transports.py - Transport utils'),
    (r'src\main.tsx', 'FIXED: PARTIAL - React entrypoint'),
    (r'src\buddy\CompanionSprite.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\buddy\useBuddyNotification.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\commands\install.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\statusline.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\components\App.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\components\Message.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\components\Onboarding.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\context\notifications.tsx', 'FIXED: PARTIAL - React context'),
    (r'src\context\stats.tsx', 'FIXED: PARTIAL - React context'),
    (r'src\entrypoints\cli.tsx', 'FIXED: PARTIAL - React entrypoint'),
    (r'src\hooks\useArrowKeyHistory.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\hooks\useChromeExtensionNotification.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\hooks\useCommandKeybindings.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\hooks\useGlobalKeybindings.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\hooks\useLspPluginRecommendation.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\hooks\usePluginRecommendationBase.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\hooks\usePromptsFromClaudeInChrome.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\hooks\useTeleportResume.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\hooks\useTypeahead.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\ink\Ansi.tsx', 'FIXED: PARTIAL - React Ink component'),
    (r'src\ink\ink.tsx', 'FIXED: PARTIAL - React Ink entrypoint'),
    (r'src\moreright\useMoreRight.tsx', 'FIXED: PARTIAL - React UI hook'),
    (r'src\screens\Doctor.tsx', 'FIXED: PARTIAL - React UI screen'),
    (r'src\screens\REPL.tsx', 'FIXED: PARTIAL - React UI screen'),
    (r'src\utils\plugins\performStartupChecks.tsx', 'FIXED: plugin_system.py - Startup checks'),
    (r'src\tools\GlobTool\UI.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\tools\GrepTool\UI.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\ink\components\AlternateScreen.tsx', 'FIXED: PARTIAL - React Ink component'),
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