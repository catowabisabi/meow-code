"""
第五輪分析批量更新腳本
更新 types, hooks, screens, schemas, moreright, coordinator, buddy, util 模組
"""
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
        # Types Module
        ("src\\types\\ids.ts", "types/ids", "SessionId/AgentId branded types + validation", "MISSING", "analyzed",
         "CRITICAL: SessionId/AgentId branded types, asSessionId/asAgentId casting, regex validation - ALL MISSING"),
        ("src\\types\\logs.ts", "types/logs", "SerializedMessage (20+ fields), LogOption, ContextCollapse*, AttributionSnapshot*, sortLogs()", "MISSING", "analyzed",
         "MAJOR: SerializedMessage, LogOption, ContextCollapseCommitEntry, AttributionSnapshotMessage, sortLogs() - ALL MISSING"),
        ("src\\types\\hooks.ts", "types/hooks", "Full hook system Zod schemas + HookCallback/HookResult", "routes/hooks.py (stub)", "analyzed",
         "MAJOR: Full Zod schemas missing, 12+ hook event types missing, HookCallback/AppState access missing, aggregated results missing"),
        ("src\\types\\command.ts", "types/command", "PromptCommand (15+ fields), LocalJSXCommandContext, ResumeEntrypoint, CommandAvailability", "routes/commands.py (partial)", "analyzed",
         "GAPS: PromptCommand details, LocalJSXCommandContext, ResumeEntrypoint, CommandAvailability - MISSING"),
        ("src\\types\\plugin.ts", "types/plugin", "PluginManifest, LoadedPlugin (15+ fields), PluginError (25+ types), PluginLoadResult", "MISSING", "analyzed",
         "CRITICAL: PluginManifest, LoadedPlugin, PluginError discriminated union, getPluginErrorMessage() - COMPLETELY MISSING"),
        ("src\\types\\textInputTypes.ts", "types/textInput", "VimMode, QueuePriority, QueuedCommand (15+ fields), OrphanedPermission", "MISSING", "analyzed",
         "GAPS: VimMode, QueuePriority, QueuedCommand, OrphanedPermission, BaseInputState/VimInputState - MISSING"),
        ("src\\types\\permissions.ts", "types/permissions", "Permission modes (7), PermissionBehavior, PermissionUpdate (5 types), YoloClassifierResult, PendingClassifierCheck", "routes/permissions.py (stub)", "analyzed",
         "MAJOR: Permission modes (acceptEdits/bypassPermissions/dontAsk/plan/auto/bubble) MISSING, PermissionUpdate discriminated union MISSING"),
        ("src\\types\\generated\\*.ts", "types/generated", "Protobuf event types: ClaudeCodeInternalEvent (30+ fields), GrowthbookExperimentEvent, EnvironmentMetadata", "MISSING", "analyzed",
         "CRITICAL: All protobuf-generated event types MISSING in Python"),

        # Hooks Module
        ("src\\hooks\\useInboxPoller.ts", "hooks/inbox", "Teammate mailbox polling (973 lines) - file-based IPC, permission routing, plan approval", "MISSING", "analyzed",
         "CRITICAL: Teammate mailbox system completely MISSING - no inbox polling API"),
        ("src\\hooks\\useSwarmInitialization.ts", "hooks/swarm", "Swarm/team initialization, hook setup for agents", "MISSING", "analyzed",
         "CRITICAL: Swarm initialization MISSING - no team context setup"),
        ("src\\hooks\\useRemoteSession.ts", "hooks/remote", "Remote CCR session WebSocket (609 lines), SDK message conversion", "routes/bridge.py (partial)", "analyzed",
         "MAJOR: WebSocket protocol for SDK messages MISSING, CCR integration MISSING"),
        ("src\\hooks\\useTaskListWatcher.ts", "hooks/tasks", "Task file watching with chokidar, claiming, ownership", "MISSING", "analyzed",
         "MAJOR: Task file watching API MISSING - tools/task_list.py is different"),
        ("src\\hooks\\useTasksV2.ts", "hooks/tasksV2", "TodoV2 task list with file watcher", "MISSING", "analyzed",
         "MAJOR: Task list V2 MISSING"),
        ("src\\hooks\\useScheduledTasks.ts", "hooks/scheduled", "Cron scheduler for tasks", "tools/cron_tool.py (partial)", "analyzed",
         "GAPS: cron_tool.py is basic stub, missing jitter/scheduler lock"),
        ("src\\hooks\\useVoice.ts", "hooks/voice", "Voice input WebSocket STT (1148 lines), audio recording/transcription", "services/voice.py (stub)", "analyzed",
         "MAJOR: Voice STT service completely MISSING"),
        ("src\\hooks\\useManagePlugins.ts", "hooks/plugins", "Plugin loading/state management", "plugins/manager.py (partial)", "analyzed",
         "GAPS: Plugin lifecycle API MISSING"),
        ("src\\hooks\\usePluginInstallationStatus.tsx", "hooks/plugins", "Plugin install status tracking, error tracking per plugin", "MISSING", "analyzed",
         "MAJOR: Plugin installation status API MISSING"),
        ("src\\hooks\\useDiffInIDE.ts", "hooks/ide", "IDE diff integration (383 lines), RPC diff display, accept/reject", "MISSING", "analyzed",
         "CRITICAL: IDE RPC bridge MISSING - no diff display API"),
        ("src\\hooks\\useIDEIntegration.tsx", "hooks/ide", "IDE auto-connect, VS Code/JetBrains integration", "MISSING", "analyzed",
         "CRITICAL: IDE integration completely MISSING"),
        ("src\\hooks\\useApiKeyVerification.ts", "hooks/auth", "API key validation", "routes/settings.py (partial)", "analyzed",
         "GAPS: No actual key verification endpoint"),
        ("src\\hooks\\usePrStatus.ts", "hooks/github", "GitHub PR status polling", "MISSING", "analyzed",
         "GAPS: No PR status polling API"),
        ("src\\hooks\\useClipboardImageHint.ts", "hooks/clipboard", "Clipboard image detection", "MISSING", "analyzed",
         "GAPS: No clipboard API"),
        ("src\\hooks\\useAssistantHistory.ts", "hooks/history", "History pagination for viewer mode", "routes/history.py (partial)", "analyzed",
         "GAPS: No paginated history endpoints"),

        # Screens Module
        ("src\\screens\\Doctor.tsx", "screens/doctor", "System diagnostics (579 lines): ripgrep, auto-update, version locks, plugin errors, MCP warnings, env validation, sandbox status", "MISSING", "analyzed",
         "CRITICAL: All Doctor diagnostics MISSING - Python has no diagnostic equivalent"),
        ("src\\screens\\REPL.tsx", "screens/repl", "Main CLI REPL (880+ lines): user input, tasks, SSH/remote, MCP tools, plugins, file history, cost tracking", "MISSING", "analyzed",
         "CRITICAL: Full REPL MISSING - Python has session CRUD only"),
        ("src\\screens\\ResumeConversation.tsx", "screens/resume", "Session resume picker (403 lines): LogSelector, cross-project detection, worktree support", "MISSING", "analyzed",
         "CRITICAL: Session picker UI MISSING - no LogSelector component"),

        # Schemas Module
        ("src\\schemas\\hooks.ts", "schemas/hooks", "Zod schemas: IfCondition, BashCommand/Prompt/Http/Agent hooks, HookMatcher (4 types)", "routes/hooks.py (stub)", "analyzed",
         "MAJOR: Zod schema equivalents MISSING - Python has flat key-value only, no discriminated union, no HTTP/agent hook types"),

        # MoreRight/Permissions Module
        ("src\\moreright\\useMoreRight.tsx", "moreright/stub", "External stub - actual permission system in src/utils/permissions/", "MISSING", "analyzed",
         "NOTE: useMoreRight.tsx is a STUB - real permissions in 14+ files under src/utils/permissions/"),
        ("src\\utils\\permissions\\", "permissions/core", "Core permission system: modes (7), behaviors (3), rules, classifier, coordinator/interactive/swarm handlers", "routes/permissions.py (stub)", "analyzed",
         "CRITICAL: Permission modes MISSING, classifier-based auto-approval MISSING, interactive dialogs MISSING, swarm handlers MISSING"),

        # Coordinator Module
        ("src\\coordinator\\coordinatorMode.ts", "coordinator/mode", "Coordinator mode (422 lines): isCoordinatorMode(), getCoordinatorUserContext(), getCoordinatorSystemPrompt()", "MISSING", "analyzed",
         "CRITICAL: Coordinator mode feature gate MISSING, session matching MISSING, worker tool allowlist MISSING, 250+ line coordinator prompt MISSING"),
        ("src\\tools\\AgentTool\\forkSubagent.ts", "coordinator/fork", "Fork subagent system (214 lines): isForkSubagentEnabled(), buildForkedMessages(), buildChildMessage()", "MISSING", "analyzed",
         "CRITICAL: Fork subagent system completely MISSING - cache optimization via placeholder tool results not implemented"),

        # Buddy Module
        ("src\\buddy\\types.ts", "buddy/types", "Companion types: rarity (5), species (18), eyes (6), hats (8), stats (5)", "MISSING", "analyzed",
         "NOTE: Buddy is CLIENT-SIDE ONLY - no Python backend needed"),
        ("src\\buddy\\companion.ts", "buddy/generation", "Companion generation: Mulberry32 PRNG, deterministic hash, cached roll", "MISSING", "analyzed",
         "NOTE: Pure client-side feature"),
        ("src\\buddy\\sprites.ts", "buddy/sprites", "ASCII sprites: 5-line animated sprites for 18 species", "MISSING", "analyzed",
         "NOTE: Pure client-side rendering"),
        ("src\\buddy\\CompanionSprite.tsx", "buddy/ui", "React component: speech bubbles, pet interaction, idle animations", "MISSING", "analyzed",
         "NOTE: Pure client-side UI"),
        ("src\\buddy\\useBuddyNotification.tsx", "buddy/notification", "Buddy notification hook: teaser window, /buddy trigger detection", "MISSING", "analyzed",
         "NOTE: Pure client-side feature"),

        # Util Subdirectories
        ("src\\utils\\cron.ts", "utils/cron", "Cron expression parsing (5-field, DST), cronToHuman()", "tools/cron_tool.py (partial)", "analyzed",
         "GAPS: cron_tool.py has basic parse only, no DST handling"),
        ("src\\utils\\cronScheduler.ts", "utils/cron-scheduler", "Scheduler (chokidar, lock, missed task detection, backoff)", "MISSING", "analyzed",
         "CRITICAL: Scheduler lock mechanism MISSING - thundering herd risk in multi-session"),
        ("src\\utils\\cronTasks.ts", "utils/cron-tasks", "Task persistence (JSON), one-time/recurring, jitter calculation", "MISSING", "analyzed",
         "GAPS: Task persistence MISSING in Python scheduler"),
        ("src\\utils\\cronTasksLock.ts", "utils/cron-lock", "O_EXCL atomic lock, PID liveness, stale lock recovery", "MISSING", "analyzed",
         "CRITICAL: Distributed lock MISSING"),
        ("src\\utils\\cronJitterConfig.ts", "utils/cron-jitter", "GrowthBook-backed jitter config for fleet-wide jitter", "MISSING", "analyzed",
         "GAPS: Dynamic jitter config MISSING"),
        ("src\\utils\\auth.ts", "utils/auth", "Auth (1533+ lines): OAuth, API key, keychain, AWS/GCP refresh, 401 handling", "MISSING", "analyzed",
         "CRITICAL: Full auth system MISSING - no OAuth, no keychain, no cloud refresh"),
        ("src\\utils\\aws.ts", "utils/aws", "AWS STS validation, INI cache clear, isValidAwsStsOutput typeguard", "MISSING", "analyzed",
         "CRITICAL: AWS integration MISSING"),
        ("src\\utils\\model\\providers.ts", "utils/providers", "APIProvider type: firstParty/Bedrock/Vertex/Foundry detection", "MISSING", "analyzed",
         "CRITICAL: Multi-provider detection MISSING"),
        ("src\\utils\\model\\bedrock.ts", "utils/bedrock", "Bedrock SDK: cross-region inference profiles, credential refresh", "MISSING", "analyzed",
         "CRITICAL: Bedrock integration MISSING"),
        ("src\\utils\\mcpValidation.ts", "utils/mcp-validation", "MCP output truncation: token estimation, image compression, GrowthBook thresholds", "MISSING", "analyzed",
         "GAPS: Unified MCP truncation module MISSING"),
        ("src\\utils\\memoryFileDetection.ts", "utils/memory-detection", "Session file type detection, auto-managed memory check, shell command analysis", "MISSING", "analyzed",
         "GAPS: Unified file type detection MISSING"),
        ("src\\utils\\cleanup.ts", "utils/cleanup", "Cleanup: 30-day old files, MCP logs, npm cache, debug logs, worktree", "MISSING", "analyzed",
         "GAPS: Cleanup system MISSING"),
        ("src\\utils\\cleanupRegistry.ts", "utils/cleanup-registry", "Global cleanup function registry for graceful shutdown", "MISSING", "analyzed",
         "GAPS: Cleanup registry MISSING"),
        ("src\\utils\\agenticSessionSearch.ts", "utils/session-search", "AI-driven cross-session semantic search, title/tag/branch extraction", "MISSING", "analyzed",
         "CRITICAL: Agentic session search MISSING - high value feature"),
        ("src\\utils\\teammateContext.ts", "utils/teammate-context", "AsyncLocalStorage for in-process teammate context", "MISSING", "analyzed",
         "GAPS: In-process teammate context MISSING"),
        ("src\\utils\\swarm\\", "utils/swarm", "Swarm system (21 files): spawnInProcess, tmux/iTerm/Pane backends, permissionSync, reconnection", "agents/teammate/ (partial)", "analyzed",
         "CRITICAL: Swarm backend abstraction MISSING, permission bridge MISSING"),
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
