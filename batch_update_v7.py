"""第七輪分析批量更新腳本
更新 tools, state, remote, components, constants, sessions, prompts, sandbox 模組"""
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
        # Tools Module
        ("src\\tools\\AgentTool\\", "tools/agent", "Agent creation/management: fork subagent, memory snapshot, advanced agent architecture", "agent_tools.py (partial)", "analyzed",
         "CRITICAL: forkSubagent/agentMemorySnapshot MISSING - Python only basic wrapper"),
        ("src\\tools\\BriefTool\\", "tools/brief", "Send messages+attachments to user (karios integration)", "MISSING", "analyzed",
         "CRITICAL: BriefTool completely MISSING - Python brief_tool.py is stub"),
        ("src\\tools\\GlobTool\\GlobTool.ts", "tools/glob", "File glob pattern matching tool", "MISSING", "analyzed",
         "CRITICAL: GlobTool MISSING - Python has grep.glob but no standalone tool"),
        ("src\\tools\\McpAuthTool\\", "tools/mcp-auth", "MCP authentication handling", "MISSING", "analyzed",
         "CRITICAL: McpAuthTool MISSING"),
        ("src\\tools\\ExitPlanModeTool\\", "tools/exit-plan", "Exit plan mode V2 with CCR approval flow", "plan_mode_tools.py (partial)", "analyzed",
         "GAPS: CCR/ulteaplan approval flow MISSING"),
        ("src\\tools\\ExitWorktreeTool\\", "tools/exit-worktree", "Exit worktree workspace", "worktree_tools.py (partial)", "analyzed",
         "GAPS: worktree_tools has enter only, no exit"),
        ("src\\tools\\TodoWriteTool\\", "tools/todo", "Todo write operations", "todo_tool.py (partial)", "analyzed",
         "GAPS: Python todo_tool.py incomplete"),

        # State Module
        ("src\\state\\AppStateStore.ts", "state/app-state", "Unified reactive AppState (574 lines): settings/tasks/MCP/plugins/notifications/team", "MISSING", "analyzed",
         "CRITICAL: Unified reactive state MISSING - Python has session_store/TaskRegistry/PluginManager separately"),
        ("src\\state\\store.ts", "state/store", "Generic Store<T> with getState/setState/subscribe", "MISSING", "analyzed",
         "CRITICAL: Reactive store pattern MISSING"),
        ("src\\state\\selectors.ts", "state/selectors", "State selectors: getViewedTeammateTask, getActiveAgentForInput", "MISSING", "analyzed",
         "CRITICAL: Selector pattern MISSING"),
        ("src\\state\\onChangeAppState.ts", "state/change-handlers", "Side effect handlers: auth cache clearing, config persistence, CCR notification", "MISSING", "analyzed",
         "CRITICAL: Change handler system MISSING"),

        # Remote Module
        ("src\\remote\\sdkMessageAdapter.ts", "remote/sdk-adapter", "SDK message conversion: CCR SDK to internal Message types", "MISSING", "analyzed",
         "CRITICAL: SDK message adapter MISSING - Python has local WS only"),
        ("src\\remote\\RemoteSessionManager.ts", "remote/session-manager", "Remote CCR session: WebSocket+HTTP dual channel, permission request/response", "MISSING", "analyzed",
         "CRITICAL: RemoteSessionManager MISSING - Python is local-only"),
        ("src\\remote\\SessionsWebSocket.ts", "remote/ws-client", "WebSocket client: reconnection/backoff, ping/pong, session not found retry", "MISSING", "analyzed",
         "CRITICAL: SessionsWebSocket MISSING"),
        ("src\\remote\\remotePermissionBridge.ts", "remote/permission-bridge", "Create synthetic AssistantMessage, Tool stub for remote tools", "MISSING", "analyzed",
         "CRITICAL: Permission bridge MISSING"),

        # Components Module
        ("src\\components\\mcp\\", "components/mcp-ui", "MCP UI: ElicitationDialog, MCPSettings, MCPListPanel, MCPToolListView (12 files)", "services/mcp/ (backend only)", "analyzed",
         "CRITICAL: MCP UI components MISSING - Python has backend only"),
        ("src\\components\\GlobalSearchDialog.tsx", "components/search", "Global search dialog (Ctrl+Shift+F)", "MISSING", "analyzed",
         "CRITICAL: GlobalSearchDialog MISSING"),
        ("src\\components\\QuickOpenDialog.tsx", "components/quick-open", "Quick open file dialog (Ctrl+Shift+P)", "MISSING", "analyzed",
         "CRITICAL: QuickOpenDialog MISSING"),
        ("src\\components\\Onboarding.tsx", "components/onboarding", "Multi-step onboarding (preflight/theme/oauth/api-key/security)", "services/tips/ (partial)", "analyzed",
         "GAPS: Full multi-step onboarding MISSING"),
        ("src\\components\\permissions\\", "components/permissions-ui", "Permission UI: 44 files for permission request dialogs", "routes/permissions.py (backend only)", "analyzed",
         "CRITICAL: Permission UI MISSING - 44 components"),

        # Constants Module
        ("src\\constants\\toolLimits.ts", "constants/tool-limits", "Tool result limits: 50K chars/100K tokens/400K bytes, 200K per message", "MISSING", "analyzed",
         "CRITICAL: All 6 tool limits MISSING"),
        ("src\\constants\\files.ts", "constants/files", "Binary file extensions set (118 extensions)", "MISSING", "analyzed",
         "CRITICAL: BINARY_EXTENSIONS set and hasBinaryExtension() MISSING"),
        ("src\\constants\\apiLimits.ts", "constants/api-limits", "API limits: 5MB image, 100 pages PDF, 20MB PDF, 100 media/request", "services/api/files_api.py (partial)", "analyzed",
         "GAPS: Only MAX_FILE_SIZE_BYTES, missing 11 specific limits"),
        ("src\\constants\\betas.ts", "constants/betas", "Beta headers: 15+ (interleaved-thinking, 1M context, effort, etc.)", "services/api/claude.py (partial)", "analyzed",
         "GAPS: Python has ~8 beta headers, missing TASK_BUDGETS/TOKEN_EFFICIENT/ADVISOR etc"),
        ("src\\constants\\spinnerVerbs.ts", "constants/spinner", "Loading verbs: 200+ spinning/loading/moving verbs", "MISSING", "analyzed",
         "NOTE: CLI-specific, low priority"),
        ("src\\constants\\figures.ts", "constants/figures", "Terminal symbols: checkmark, arrow, bullet etc", "MISSING", "analyzed",
         "NOTE: CLI-specific, low priority"),

        # Sessions Module
        ("src\\assistant\\sessionHistory.ts", "sessions/history", "History pagination: fetchLatestEvents/fetchOlderEvents with cursor", "MISSING", "analyzed",
         "CRITICAL: History pagination MISSING - Python has list only"),
        ("src\\services\\SessionMemory\\sessionMemory.ts", "sessions/memory", "AI-powered memory extraction via forked subagent with thresholds", "services/session_memory.py (KV only)", "analyzed",
         "CRITICAL: AI extraction MISSING - Python only basic KV store"),
        ("src\\services\\compact\\sessionMemoryCompact.ts", "sessions/memory-compact", "Session memory compaction: adjustIndexToPreserveAPIInvariants", "services/compact/session_memory.py (stub)", "analyzed",
         "CRITICAL: Full logic MISSING - try_session_memory_compaction() returns None"),
        ("src\\services\\api\\sessionIngress.ts", "sessions/ingress", "Session log persistence: appendSessionLog with retry/409 handling", "services/api/session_ingress.py (partial)", "analyzed",
         "GAPS: Python has basic implementation, missing some error handling"),
        ("src\\commands\\session\\index.ts", "sessions/remote-cmd", "Remote session mode: URL and QR code display", "MISSING", "analyzed",
         "NOTE: CLI-specific"),

        # Prompts Module
        ("src\\constants\\prompts.ts", "prompts/system", "System prompt (918 lines): Proactive/Kairos/Feature Flags/Session Guidance", "prompts/builder.py (20% coverage)", "analyzed",
         "CRITICAL: Python implements ~20% - missing Proactive/Kairos/Feature Flags/complex sections"),
        ("src\\constants\\systemPromptSections.ts", "prompts/sections", "Section caching: getSystemPromptSectionCache()", "prompts/cache.py (partial)", "analyzed",
         "GAPS: Python has basic caching, TypeScript has complex cache management"),
        ("src\\utils\\systemPrompt.ts", "prompts/utils", "Effective system prompt building, subagent enhancement", "MISSING", "analyzed",
         "CRITICAL: enhanceSystemPromptWithEnvDetails() MISSING"),
        ("src\\prompts\\", "prompts/missing", "Model knowledge cutoff, output style config, REPL mode, scratchpad", "MISSING", "analyzed",
         "CRITICAL: 20+ specific prompt features MISSING"),

        # Sandbox Module
        ("src\\utils\\sandbox\\sandbox-adapter.ts", "sandbox/adapter", "SandboxManager (990 lines): dependency check/violation tracking/settings subscription", "sandbox/sandboxed_shell.py (partial)", "analyzed",
         "CRITICAL: Python has basic adapter, MISSING: getSandboxUnavailableReason/violationStore"),
        ("src\\tools\\BashTool\\shouldUseSandbox.ts", "sandbox/should-use", "shouldUseSandbox() decision: compound command parsing, excluded patterns", "MISSING", "analyzed",
         "CRITICAL: shouldUseSandbox() decision logic MISSING"),
        ("src\\utils\\sandbox\\sandbox-ui-utils.ts", "sandbox/ui", "Sandbox UI utilities", "MISSING", "analyzed",
         "NOTE: CLI-specific UI"),
        ("src\\commands\\sandbox-toggle\\", "sandbox/toggle", "/sandbox command: exclude subcommand, policy lock detection", "MISSING", "analyzed",
         "CRITICAL: /sandbox CLI command MISSING"),
        ("src\\components\\sandbox\\", "sandbox/components", "Sandbox UI components: settings/dependencies/violations/doctor", "MISSING", "analyzed",
         "NOTE: CLI-specific UI"),
        ("src\\entrypoints\\sandboxTypes.ts", "sandbox/types", "Zod schemas for sandbox config validation", "sandbox/config.py (partial)", "analyzed",
         "GAPS: Python has dataclasses, no Zod validation"),
    ]

    total = 0
    for src_path, category, summary, api_path, status, notes in updates:
        rows = update_record(src_path, category, summary, api_path, status, notes)
        if rows > 0:
            total += rows
            print(f"[+] Updated: {src_path[:45]}...")
        else:
            print(f"[-] Not found: {src_path[:45]}...")

    print(f"\nTotal records updated: {total}")

if __name__ == "__main__":
    main()
