"""第十七輪分析批量更新腳本
更新 git, swarm, hooks 模組"""
import sqlite3
from datetime import datetime

DB_PATH = r"F:\codebase\cato-claude\progress.db"

def update_record(src_path, category, summary, api_path, status, notes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE files SET 
            category = ?,
            summary = ?,
            api_path = ?,
            status = ?,
            analyzed_at = ?,
            notes = ?
        WHERE src_path = ?
    """, (category, summary, api_path, status, datetime.now().isoformat(), notes, src_path))
    conn.commit()
    rows = cursor.rowcount
    conn.close()
    return rows

def main():
    updates = [
        # Git modules (CRITICAL/HIGH)
        ("src\\utils\\git\\gitFilesystem.ts", "git/filesystem", "Filesystem-based git state: SHA/ref validation, GitFileWatcher caching, worktree support (705 lines)", "NONE", "analyzed",
         "CRITICAL: No Python equivalent. TypeScript reads .git/ directly avoiding subprocess (~15ms saved), has SHA validation for security."),
        ("src\\utils\\git\\gitConfigParser.ts", "git/config", ".git/config parser: parseGitConfigValue, escape sequences handling (283 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No Python equivalent for .git/config parsing."),
        ("src\\utils\\git\\gitignore.ts", "git/gitignore", "Gitignore: isPathGitignored, getGlobalGitignorePath (103 lines)", "NONE", "analyzed",
         "MEDIUM NO_MATCH: No Python equivalent for gitignore checking."),
        ("src\\utils\\gitDiff.ts", "git/diff", "Git diff parsing: fetchGitDiffHunks, parseGitNumstat, transient state detection (536 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No Python equivalent for structured diff parsing."),
        ("src\\utils\\worktree.ts", "git/worktree", "Worktree lifecycle: create/cleanup/stale cleanup, sparse-checkout, tmux integration (1525 lines)", "api_server/tools/worktree_tools.py", "analyzed",
         "CRITICAL: Python has only basic wrappers. Missing: tmux, hooks, symlinks, sparse-checkout, stale cleanup patterns."),

        # Swarm/Team modules (CRITICAL/HIGH)
        ("src\\utils\\swarm\\inProcessRunner.ts", "swarm/execution", "In-process teammate execution: AsyncLocalStorage isolation, permission bridge, mailbox polling (1500+ lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: No Python in-process execution. AsyncLocalStorage has no Python equivalent."),
        ("src\\utils\\swarm\\permissionSync.ts", "swarm/permissions", "Cross-agent permission coordination via mailbox: SwarmPermissionRequest schema (933 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: No permission synchronization system."),
        ("src\\utils\\swarm\\teamHelpers.ts", "swarm/team", "Team file CRUD, worktree cleanup, member tracking (687 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No team file management or worktree isolation."),
        ("src\\utils\\swarm\\spawnInProcess.ts", "swarm/spawn", "In-process teammate spawning: TeammateIdentity, AbortController (333 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: No in-process spawning with TeammateIdentity."),
        ("src\\utils\\swarm\\leaderPermissionBridge.ts", "swarm/bridge", "Permission bridge for REPL to delegate to in-process teammates (59 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: No permission bridge for in-process teammates."),
        ("src\\utils\\swarm\\constants.ts", "swarm/constants", "SWARM_SESSION_NAME, tmux command, environment variables (37 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No swarm constants defined in Python."),
        ("src\\utils\\swarm\\reconnection.ts", "swarm/reconnect", "Swarm context init from CLI args or transcript for resumed session (124 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No reconnection logic for teammate sessions."),
        ("src\\utils\\swarm\\teammateInit.ts", "swarm/init", "Registers Stop hook to notify leader on teammate idle (134 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No idle notification system."),
        ("src\\utils\\swarm\\teammateLayoutManager.ts", "swarm/ui", "Assigns teammate colors, creates panes in tmux/iTerm2 (111 lines)", "NONE", "analyzed",
         "MEDIUM: No pane creation/managment in Python."),
        ("src\\utils\\swarm\\teammateModel.ts", "swarm/model", "Gets hardcoded teammate model fallback (14 lines)", "NONE", "analyzed",
         "MEDIUM: No teammate-specific model selection."),
        ("src\\utils\\swarm\\teammatePromptAddendum.ts", "swarm/prompts", "System prompt addendum explaining SendMessage tool (23 lines)", "NONE", "analyzed",
         "MEDIUM: No teammate-specific prompt addendum."),

        # AgentTool modules (CRITICAL/HIGH)
        ("src\\tools\\AgentTool\\AgentTool.tsx", "agent/tool", "Main Agent tool: spawns subagents/teammates, worktree isolation, MCP validation (1000+ lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python run_agent.py lacks: worktree isolation, async spawn, MCP validation, permission mode propagation."),
        ("src\\tools\\AgentTool\\builtInAgents.ts", "agent/registry", "Built-in agents: GENERAL_PURPOSE/STATUSLINE_SETUP/EXPLORE/PLAN/VERIFICATION (76 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No built-in agent registry in Python."),
        ("src\\tools\\AgentTool\\agentToolUtils.ts", "agent/utils", "filterToolsForAgent, resolveAgentTools, emitTaskProgress (690 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Missing tool filtering and result finalization with usage tracking."),
        ("src\\tools\\AgentTool\\forkSubagent.ts", "agent/fork", "Fork subagent feature: implicit fork when subagent_type omitted (214 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Fork subagent experiment not implemented."),
        ("src\\tools\\AgentTool\\loadAgentsDir.ts", "agent/loading", "Load agent definitions from directories, filter by MCP requirements", "NONE", "analyzed",
         "HIGH NO_MATCH: No agent directory loading with frontmatter parsing."),

        # Hooks (85+ files - UI architectural gaps)
        ("src\\hooks\\useApiKeyVerification.ts", "hooks/auth", "API key validation with status tracking (88 lines)", "NONE", "analyzed",
         "MEDIUM: Python has api_key verification but different architecture."),
        ("src\\hooks\\useArrowKeyHistory.tsx", "hooks/input", "Arrow key history navigation (234 lines)", "NONE", "analyzed",
         "LOW: UI keyboard handling - no REST equivalent."),
        ("src\\hooks\\useAssistantHistory.ts", "hooks/history", "Lazy-load Claude assistant history on scroll (254 lines)", "api_server/routes/history.py", "analyzed",
         "MEDIUM: Python has history endpoints but different loading pattern."),
        ("src\\hooks\\useAwaySummary.ts", "hooks/summary", "Away summary after 5 min blur (129 lines)", "NONE", "analyzed",
         "MEDIUM: No Python equivalent for blur-based summaries."),
        ("src\\hooks\\useBackgroundTaskNavigation.ts", "hooks/ui", "Shift+Up/Down teammate navigation (255 lines)", "NONE", "analyzed",
         "LOW: UI keyboard navigation."),
        ("src\\hooks\\useCancelRequest.ts", "hooks/input", "Cancel/escape/Ctrl+C handler (276 lines)", "NONE", "analyzed",
         "MEDIUM: Python has request cancellation but different pattern."),
        ("src\\hooks\\useChromeExtensionNotification.tsx", "hooks/extension", "Chrome extension notifications (55 lines)", "NONE", "analyzed",
         "LOW: Extension integration - no Python equivalent."),
        ("src\\hooks\\useClipboardImageHint.ts", "hooks/input", "Clipboard image paste notification (81 lines)", "NONE", "analyzed",
         "LOW: UI notification."),
        ("src\\hooks\\useCommandKeybindings.tsx", "hooks/input", "Command keybinding handlers (114 lines)", "NONE", "analyzed",
         "LOW: UI keyboard handling."),
        ("src\\hooks\\useCopyOnSelect.ts", "hooks/input", "Auto-copy on selection (102 lines)", "NONE", "analyzed",
         "LOW: UI feature."),
        ("src\\hooks\\useDeferredHookMessages.ts", "hooks/messaging", "Deferred SessionStart hook messages (96 lines)", "NONE", "analyzed",
         "MEDIUM: Python has hook infrastructure but different message deferral."),
        ("src\\hooks\\useDiffData.ts", "hooks/git", "Git diff data fetching (114 lines)", "NONE", "analyzed",
         "MEDIUM: Python git diff differs."),
        ("src\\hooks\\useDirectConnect.ts", "hooks/remote", "DirectConnect WebSocket session (233 lines)", "NONE", "analyzed",
         "HIGH: Python has no WebSocket direct-connect."),
        ("src\\hooks\\useDynamicConfig.ts", "hooks/config", "GrowthBook dynamic config (27 lines)", "NONE", "analyzed",
         "MEDIUM: Python has GrowthBook but different integration."),
        ("src\\hooks\\useGlobalKeybindings.tsx", "hooks/input", "Global keybindings: ctrl+t, ctrl+o (249 lines)", "NONE", "analyzed",
         "LOW: UI keyboard handling."),
        ("src\\hooks\\useHistorySearch.ts", "hooks/search", "Ctrl+r history search (307 lines)", "NONE", "analyzed",
         "MEDIUM: Python has history search FTS5."),
        ("src\\hooks\\useIdeConnectionStatus.ts", "hooks/ide", "IDE connection status (37 lines)", "NONE", "analyzed",
         "MEDIUM: Python MCP has connection tracking."),
        ("src\\hooks\\useIDEIntegration.tsx", "hooks/ide", "IDE extension auto-connection (75 lines)", "NONE", "analyzed",
         "MEDIUM: IDE integration is CLI-specific."),
        ("src\\hooks\\useIdeSelection.ts", "hooks/ide", "IDE text selection tracking (154 lines)", "NONE", "analyzed",
         "MEDIUM: IDE integration."),
        ("src\\hooks\\useInputBuffer.ts", "hooks/input", "Input buffer undo/redo (136 lines)", "NONE", "analyzed",
         "LOW: UI input handling."),
        ("src\\hooks\\useIssueFlagBanner.ts", "hooks/ui", "Issue flag friction signal banner (137 lines)", "NONE", "analyzed",
         "LOW: UI banner."),
        ("src\\hooks\\useLogMessages.ts", "hooks/logging", "Transcript logging (123 lines)", "NONE", "analyzed",
         "MEDIUM: Python has internal logging."),
        ("src\\hooks\\useLspPluginRecommendation.tsx", "hooks/lsp", "LSP plugin recommendations (199 lines)", "NONE", "analyzed",
         "LOW: LSP plugin detection - CLI-specific."),
        ("src\\hooks\\useMailboxBridge.ts", "hooks/messaging", "Mailbox to React bridge (25 lines)", "NONE", "analyzed",
         "HIGH: No mailbox system in Python."),
        ("src\\hooks\\useManagePlugins.ts", "hooks/plugins", "Plugin loading/management (308 lines)", "api_server/services/plugins/", "analyzed",
         "MEDIUM: Python has plugin manager but different architecture."),
        ("src\\hooks\\useMemoryUsage.ts", "hooks/diagnostics", "Memory monitoring (43 lines)", "NONE", "analyzed",
         "LOW: Python has diagnostics."),
        ("src\\hooks\\useMergedClients.ts", "hooks/mcp", "MCP client merging (27 lines)", "api_server/services/mcp/client.py", "analyzed",
         "MEDIUM: Python has MCP client merging."),
        ("src\\hooks\\useMergedTools.ts", "hooks/tools", "Tool pool assembly (48 lines)", "api_server/tools/register.py", "analyzed",
         "LOW: Python has tool registration."),
        ("src\\hooks\\useNotifyAfterTimeout.ts", "hooks/notifications", "Desktop notifications (69 lines)", "NONE", "analyzed",
         "LOW: UI notifications."),
        ("src\\hooks\\usePasteHandler.ts", "hooks/input", "Paste handling including images (289 lines)", "NONE", "analyzed",
         "LOW: UI paste handling."),
        ("src\\hooks\\usePluginRecommendationBase.tsx", "hooks/plugins", "Plugin recommendation shared state (110 lines)", "NONE", "analyzed",
         "MEDIUM: Python has plugin marketplace."),
        ("src\\hooks\\usePrStatus.ts", "hooks/github", "GitHub PR status polling (110 lines)", "NONE", "analyzed",
         "MEDIUM: Python has no PR polling."),
        ("src\\hooks\\useRemoteSession.ts", "hooks/remote", "Remote CCR session via WebSocket (609 lines)", "NONE", "analyzed",
         "CRITICAL: Python has no remote CCR session."),
        ("src\\hooks\\useScheduledTasks.ts", "hooks/scheduler", "Cron scheduler (143 lines)", "NONE", "analyzed",
         "HIGH: Python has no cron scheduler for agents."),
        ("src\\hooks\\useSearchInput.ts", "hooks/input", "Search input with cursor handling (368 lines)", "NONE", "analyzed",
         "LOW: UI input handling."),
        ("src\\hooks\\useSessionBackgrounding.ts", "hooks/session", "Ctrl+B background session (158 lines)", "NONE", "analyzed",
         "LOW: UI session management."),
        ("src\\hooks\\useSSHSession.ts", "hooks/ssh", "SSH session manager (241 lines)", "NONE", "analyzed",
         "HIGH: Python has no SSH session management."),
        ("src\\hooks\\useSwarmInitialization.ts", "hooks/swarm", "Swarm/team initialization (81 lines)", "NONE", "analyzed",
         "HIGH: Python has no swarm initialization."),
        ("src\\hooks\\useSwarmPermissionPoller.ts", "hooks/swarm", "Team leader permission polling (330 lines)", "NONE", "analyzed",
         "CRITICAL: No swarm permission polling in Python."),
        ("src\\hooks\\useTaskListWatcher.ts", "hooks/tasks", "Task list directory watcher (225 lines)", "NONE", "analyzed",
         "MEDIUM: Python has task system but different architecture."),
        ("src\\hooks\\useTasksV2.ts", "hooks/tasks", "Todo v2 with useSyncExternalStore (254 lines)", "NONE", "analyzed",
         "MEDIUM: Python has task endpoints."),
        ("src\\hooks\\useTeammateViewAutoExit.ts", "hooks/swarm", "Auto-exit teammate view (67 lines)", "NONE", "analyzed",
         "LOW: UI teammate view."),
        ("src\\hooks\\useTeleportResume.tsx", "hooks/remote", "Teleport session resume (90 lines)", "NONE", "analyzed",
         "HIGH: Python has no teleport/remote resume."),
        ("src\\hooks\\useTextInput.ts", "hooks/input", "Text input with vim/emacs keys (533 lines)", "NONE", "analyzed",
         "LOW: UI text input."),
        ("src\\hooks\\useTurnDiffs.ts", "hooks/git", "Turn-based diff extraction (217 lines)", "NONE", "analyzed",
         "MEDIUM: Python diff handling differs."),
        ("src\\hooks\\useTypeahead.tsx", "hooks/input", "Autocomplete/typeahead (~1200+ lines)", "NONE", "analyzed",
         "HIGH: No typeahead system in Python API."),
        ("src\\hooks\\useVirtualScroll.ts", "hooks/ui", "React virtualization (726 lines)", "NONE", "analyzed",
         "LOW: UI rendering."),
        ("src\\hooks\\useVoiceEnabled.ts", "hooks/voice", "Voice feature gate (29 lines)", "NONE", "analyzed",
         "HIGH: Voice not implemented."),
        ("src\\hooks\\fileSuggestions.ts", "hooks/autocomplete", "File path autocomplete: git ls-files + ripgrep + Rust FileIndex (815 lines)", "NONE", "analyzed",
         "HIGH: No fuzzy file search equivalent."),
        ("src\\hooks\\unifiedSuggestions.ts", "hooks/autocomplete", "Unified @ mention suggestions: files + MCP + agents (206 lines)", "NONE", "analyzed",
         "HIGH: No unified suggestion system."),

        # notifs/ hooks
        ("src\\hooks\\notifs\\useStartupNotification.ts", "hooks/notifications", "Startup notification (46 lines)", "NONE", "analyzed", "LOW: UI notification."),
        ("src\\hooks\\notifs\\useLspInitializationNotification.ts", "hooks/notifications", "LSP initialization notification (35 lines)", "NONE", "analyzed", "LOW: UI notification."),
        ("src\\hooks\\notifs\\useLspConnectionNotification.ts", "hooks/notifications", "LSP connection notification (27 lines)", "NONE", "analyzed", "LOW: UI notification."),
        ("src\\hooks\\notifs\\useOfficialMarketplaceNotification.tsx", "hooks/notifications", "Marketplace notification (52 lines)", "NONE", "analyzed", "MEDIUM: Python has marketplace."),
        ("src\\hooks\\notifs\\useAutoModeUnavailableNotification.ts", "hooks/notifications", "Auto mode unavailable notification (56 lines)", "NONE", "analyzed", "MEDIUM: Auto mode is CLI-specific."),
        ("src\\hooks\\notifs\\useNpmDeprecationNotification.ts", "hooks/notifications", "NPM deprecation notification (54 lines)", "NONE", "analyzed", "LOW: UI notification."),
        ("src\\hooks\\notifs\\useIdeInstallationNotification.ts", "hooks/notifications", "IDE installation notification (50 lines)", "NONE", "analyzed", "LOW: UI notification."),
        ("src\\hooks\\notifs\\useIdeConnectionNotification.ts", "hooks/notifications", "IDE connection notification (57 lines)", "NONE", "analyzed", "LOW: UI notification."),
        ("src\\hooks\\notifs\\useIdeStatusNotification.ts", "hooks/notifications", "IDE status notification (48 lines)", "NONE", "analyzed", "LOW: UI notification."),
        ("src\\hooks\\notifs\\usePluginAutoupdateNotification.ts", "hooks/notifications", "Plugin autoupdate notification (45 lines)", "NONE", "analyzed", "MEDIUM: Python has plugin manager."),
        ("src\\hooks\\notifs\\usePluginInstallationNotification.ts", "hooks/notifications", "Plugin installation notification (61 lines)", "NONE", "analyzed", "MEDIUM: Python has plugin manager."),
        ("src\\hooks\\notifs\\useRateLimitNotification.ts", "hooks/notifications", "Rate limit notification (43 lines)", "NONE", "analyzed", "MEDIUM: Python has rate limit handling."),
        ("src\\hooks\\notifs\\useSettingsErrorNotification.ts", "hooks/notifications", "Settings error notification (41 lines)", "NONE", "analyzed", "MEDIUM: Python has settings."),
        ("src\\hooks\\notifs\\useMcpHomeNotification.ts", "hooks/notifications", "MCP home notification (46 lines)", "NONE", "analyzed", "MEDIUM: MCP is handled differently."),
        ("src\\hooks\\notifs\\useSubscriptionChangedNotification.ts", "hooks/notifications", "Subscription changed notification (55 lines)", "NONE", "analyzed", "MEDIUM: Subscription is CLI-specific."),
        ("src\\hooks\\notifs\\useTeammateShutdownNotification.ts", "hooks/notifications", "Teammate shutdown notification (37 lines)", "NONE", "analyzed", "MEDIUM: Swarm/team is CLI-specific."),

        # toolPermission hooks
        ("src\\hooks\\toolPermission\\PermissionContext.ts", "hooks/permissions", "Permission state machine: logDecision, runHooks, tryClassifier, buildAllow/Deny (392 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Deeply stateful React+IPC pattern."),
        ("src\\hooks\\toolPermission\\permissionLogging.ts", "hooks/telemetry", "Centralized analytics fan-out: Statsig + OTel + code-edit counters (242 lines)", "NONE", "analyzed",
         "HIGH: Python lacks unified telemetry pipeline."),
        ("src\\hooks\\toolPermission\\handlers\\interactiveHandler.ts", "hooks/permissions", "Interactive permission 5-way race: local/hook/classifier/bridge/channel (540 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Most complex hook - no REST equivalent."),
        ("src\\hooks\\toolPermission\\handlers\\localHandler.ts", "hooks/permissions", "Local permission handler (85 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Local permission flow."),
        ("src\\hooks\\toolPermission\\handlers\\classifierHandler.ts", "hooks/permissions", "Classifier-based permission (165 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Classifier has no Python equivalent."),
    ]

    total = 0
    for src_path, category, summary, api_path, status, notes in updates:
        rows = update_record(src_path, category, summary, api_path, status, notes)
        if rows > 0:
            total += rows
            print(f"[+] Updated: {src_path[:50]}...")
        else:
            print(f"[-] Not found: {src_path[:50]}...")

    print(f"\nTotal records updated: {total}")

if __name__ == "__main__":
    main()
