import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\hooks\fileSuggestions.ts', 'FIXED: hooks_system.py - FileSuggestions'),
    (r'src\hooks\unifiedSuggestions.ts', 'FIXED: hooks_system.py - UnifiedSuggestions'),
    (r'src\hooks\useAfterFirstRender.ts', 'FIXED: hooks_system.py - UseAfterFirstRender'),
    (r'src\hooks\useApiKeyVerification.ts', 'FIXED: hooks_system.py - UseApiKeyVerification'),
    (r'src\hooks\useAssistantHistory.ts', 'FIXED: hooks_system.py - UseAssistantHistory'),
    (r'src\hooks\useAwaySummary.ts', 'FIXED: hooks_system.py - UseAwaySummary'),
    (r'src\hooks\useBackgroundTaskNavigation.ts', 'FIXED: hooks_system.py - UseBackgroundTaskNavigation'),
    (r'src\hooks\useBlink.ts', 'FIXED: hooks_system.py - UseBlink'),
    (r'src\hooks\useCancelRequest.ts', 'FIXED: hooks_system.py - UseCancelRequest'),
    (r'src\hooks\useClipboardImageHint.ts', 'FIXED: hooks_system.py - UseClipboardImageHint'),
    (r'src\hooks\useCommandQueue.ts', 'FIXED: hooks_system.py - UseCommandQueue'),
    (r'src\hooks\useCopyOnSelect.ts', 'FIXED: hooks_system.py - UseCopyOnSelect'),
    (r'src\hooks\useDeferredHookMessages.ts', 'FIXED: hooks_system.py - UseDeferredHookMessages'),
    (r'src\hooks\useDiffData.ts', 'FIXED: hooks_system.py - UseDiffData'),
    (r'src\hooks\useDiffInIDE.ts', 'FIXED: ide_proxy.py - UseDiffInIDE'),
    (r'src\hooks\useDirectConnect.ts', 'FIXED: transports.py - UseDirectConnect'),
    (r'src\hooks\useDoublePress.ts', 'FIXED: hooks_system.py - UseDoublePress'),
    (r'src\hooks\useDynamicConfig.ts', 'FIXED: enhanced_settings.py - UseDynamicConfig'),
    (r'src\hooks\useElapsedTime.ts', 'FIXED: cli_utils.py - UseElapsedTime'),
    (r'src\hooks\useExitOnCtrlCD.ts', 'FIXED: hooks_system.py - UseExitOnCtrlCD'),
    (r'src\hooks\useExitOnCtrlCDWithKeybindings.ts', 'FIXED: hooks_system.py - UseExitOnCtrlCDWithKeybindings'),
    (r'src\hooks\useFileHistorySnapshotInit.ts', 'FIXED: hooks_system.py - UseFileHistorySnapshotInit'),
    (r'src\hooks\useHistorySearch.ts', 'FIXED: hooks_system.py - UseHistorySearch'),
    (r'src\hooks\useIdeAtMentioned.ts', 'FIXED: ide_proxy.py - UseIdeAtMentioned'),
    (r'src\hooks\useIdeConnectionStatus.ts', 'FIXED: transports.py - UseIdeConnectionStatus'),
    (r'src\hooks\useIdeLogging.ts', 'FIXED: cli_utils.py - UseIdeLogging'),
    (r'src\hooks\useIdeSelection.ts', 'FIXED: ide_proxy.py - UseIdeSelection'),
    (r'src\hooks\useInboxPoller.ts', 'FIXED: hooks_system.py - InboxPoller'),
    (r'src\hooks\useInputBuffer.ts', 'FIXED: hooks_system.py - UseInputBuffer'),
    (r'src\hooks\useIssueFlagBanner.ts', 'FIXED: hooks_system.py - UseIssueFlagBanner'),
    (r'src\hooks\useLogMessages.ts', 'FIXED: cli_utils.py - UseLogMessages'),
    (r'src\hooks\useMailboxBridge.ts', 'FIXED: hooks_system.py - UseMailboxBridge'),
    (r'src\hooks\useMainLoopModel.ts', 'FIXED: query_engine.py - UseMainLoopModel'),
    (r'src\hooks\useManagePlugins.ts', 'FIXED: plugin_system.py - UseManagePlugins'),
    (r'src\hooks\useMemoryUsage.ts', 'FIXED: analytics.py - UseMemoryUsage'),
    (r'src\hooks\useMergedClients.ts', 'FIXED: hooks_system.py - UseMergedClients'),
    (r'src\hooks\useMergedCommands.ts', 'FIXED: hooks_system.py - UseMergedCommands'),
    (r'src\hooks\useMergedTools.ts', 'FIXED: enhanced_types.py - UseMergedTools'),
    (r'src\hooks\useMinDisplayTime.ts', 'FIXED: cli_utils.py - UseMinDisplayTime'),
    (r'src\hooks\useNotifyAfterTimeout.ts', 'FIXED: cli_utils.py - UseNotifyAfterTimeout'),
    (r'src\hooks\usePasteHandler.ts', 'FIXED: hooks_system.py - UsePasteHandler'),
    (r'src\hooks\usePromptSuggestion.ts', 'FIXED: hooks_system.py - UsePromptSuggestion'),
    (r'src\hooks\usePrStatus.ts', 'FIXED: hooks_system.py - UsePrStatus'),
    (r'src\hooks\useQueueProcessor.ts', 'FIXED: hooks_system.py - UseQueueProcessor'),
    (r'src\hooks\useRemoteSession.ts', 'FIXED: remote_swarm.py - RemoteSession'),
    (r'src\hooks\useScheduledTasks.ts', 'FIXED: cron_scheduler.py - UseScheduledTasks'),
    (r'src\hooks\useSearchInput.ts', 'FIXED: hooks_system.py - UseSearchInput'),
    (r'src\hooks\useSessionBackgrounding.ts', 'FIXED: enhanced_session.py - UseSessionBackgrounding'),
    (r'src\hooks\useSettings.ts', 'FIXED: enhanced_settings.py - UseSettings'),
    (r'src\hooks\useSettingsChange.ts', 'FIXED: enhanced_settings.py - UseSettingsChange'),
    (r'src\hooks\useSkillImprovementSurvey.ts', 'FIXED: hooks_system.py - UseSkillImprovementSurvey'),
    (r'src\hooks\useSkillsChange.ts', 'FIXED: hooks_system.py - UseSkillsChange'),
    (r'src\hooks\useSwarmPermissionPoller.ts', 'FIXED: remote_swarm.py - SwarmPermissionPoller'),
    (r'src\hooks\useTerminalSize.ts', 'FIXED: cli_utils.py - UseTerminalSize'),
    (r'src\hooks\useTimeout.ts', 'FIXED: cli_utils.py - UseTimeout'),
    (r'src\hooks\useUpdateNotification.ts', 'FIXED: cli_utils.py - UseUpdateNotification'),
    (r'src\hooks\useVimInput.ts', 'FIXED: hooks_system.py - UseVimInput'),
    (r'src\hooks\useVoice.ts', 'FIXED: terminal_voice.py - VoiceRecorder'),
    (r'src\hooks\useWorktree.ts', 'FIXED: worktree_tools.py - UseWorktree'),
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