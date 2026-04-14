"""第十二輪分析批量更新腳本
更新 state, tools, remote, voice 模組"""
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
        # State module
        ("src\\state\\AppStateStore.ts", "state/app", "Central app state container: settings/tasks/MCP/plugins/notifications/speculation/teamContext/inbox (574 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: No Python equivalent. Python api_server has no reactive in-memory state store matching AppState scope."),
        ("src\\state\\AppState.tsx", "state/react", "React Context Provider: useAppState, useSetAppState, useAppStateStore hooks (205 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Pure React/UI pattern. No Python equivalent - would require WebSocket push/polling architecture."),
        ("src\\state\\store.ts", "state/factory", "Simple observable store factory: getState/setState/subscribe (39 lines)", "api_server/services/session_store.py", "analyzed",
         "HIGH: Python SessionStore.save/load are async file-based, not reactive. No in-memory observable store equivalent."),
        ("src\\state\\selectors.ts", "state/ui", "getViewedTeammateTask, getActiveAgentForInput selectors (77 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: UI-specific selectors for input routing. Python API is backend-only."),
        ("src\\state\\onChangeAppState.ts", "state/sidefx", "Side-effect handlers: CCR sync, auth cache clearing, env vars reapplication (176 lines)", "NONE", "analyzed",
         "MEDIUM NO_MATCH: CLI-specific side effects tied to CCR bridge, OpenTelemetry, AWS/GCP."),
        ("src\\state\\teammateViewHelpers.ts", "state/ui", "enterTeammateView, exitTeammateView, stopOrDismissAgent (146 lines)", "NONE", "analyzed",
         "MEDIUM NO_MATCH: Pure UI panel logic. No Python equivalent."),
        ("src\\bootstrap\\state.ts", "state/bootstrap", "Session-level bootstrap state: telemetry counters, cron tasks, invokedSkills, beta headers (1578 lines)", "NONE", "analyzed",
         "HIGH: Python SessionStore only handles JSON serialization. Missing: telemetry AttributedCounter, session cron tasks, invokedSkills Map, beta header latches."),

        # Remote CCR module (CRITICAL)
        ("src\\remote\\RemoteSessionManager.ts", "remote/session", "Manages CCR session lifecycle: WebSocket subscription, HTTP POST, permission flow (347 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python ws/chat.py handles local sessions only. No CCR session coordination."),
        ("src\\remote\\SessionsWebSocket.ts", "remote/websocket", "WebSocket client for /v1/sessions/ws/{id}/subscribe with reconnection/heartbeat (408 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python lacks CCR-specific subscription endpoint, reconnection backoff, 4001 retry handling."),
        ("src\\remote\\sdkMessageAdapter.ts", "remote/protocol", "Converts SDK messages (assistant/user/stream_event/result/system/tool_progress) to REPL format (307 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python has no convertSDKMessage equivalent. ws/protocol.py defines local types only."),
        ("src\\remote\\remotePermissionBridge.ts", "remote/permissions", "Creates synthetic AssistantMessages and Tool stubs for remote permission requests (84 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No Python equivalent for synthetic message creation when CCR runs unknown tools."),

        # Voice/STT module (CRITICAL)
        ("src\\hooks\\useVoice.ts", "voice/input", "Hold-to-talk voice input using Anthropic voice_stream WebSocket API (1148 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python has local audio recording (SoX) but ZERO WebSocket STT integration."),
        ("src\\services\\voiceStreamSTT.ts", "voice/stt", "WebSocket client for Anthropic voice_stream API: OAuth, keepalive, finalize (549 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python has no voice_stream WebSocket client equivalent."),
        ("src\\voice\\voiceModeEnabled.ts", "voice/config", "Feature gating: GrowthBook VOICE_MODE flag + OAuth auth check (91 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python voice.py has no auth/feature-gate checks."),
        ("src\\hooks\\useVoiceEnabled.ts", "voice/react", "React hook: user intent + auth + GrowthBook kill-switch (29 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: React hook has no Python equivalent."),

        # Tools module (key files)
        ("src\\tools\\BashTool\\BashTool.tsx", "tools/shell", "Shell execution: sed preview, auto-backgrounding, image output, sandbox, progress streaming (1150 lines)", "api_server/tools/bash.py", "analyzed",
         "HIGH: Python bash.py (393 lines) missing: sed preview simulation, auto-background logic, image dimension capping, returnCodeInterpretation."),
        ("src\\tools\\FileReadTool\\FileReadTool.ts", "tools/files", "Multi-format reader: text/image/PDF/notebook with token budgeting (1187 lines)", "api_server/tools/file_tools.py", "analyzed",
         "HIGH: Python missing: PDF reading, image resize/compress, Jupyter notebook support, token-based deduplication."),
        ("src\\tools\\WebFetchTool\\WebFetchTool.ts", "tools/web", "URL fetch: redirect detection, markdown conversion, preapproved hosts (322 lines)", "api_server/tools/web_fetch.py", "analyzed",
         "MEDIUM: Python missing: redirect detection, markdown conversion with prompt application, preapproved host list."),
        ("src\\tools\\AgentTool\\AgentTool.tsx", "tools/agent", "Subagent spawning: worktree isolation, fork mode, remote exec, MCP validation (1000+ lines)", "api_server/tools/agent.py", "analyzed",
         "HIGH: Python missing: worktree isolation, fork subagent mode, remote execution, MCP requirement checking."),
        ("src\\tools\\PowerShellTool\\PowerShellTool.tsx", "tools/shell", "PowerShell execution with security validation (12 files)", "NONE", "analyzed",
         "HIGH NO_MATCH: No Python PowerShell tool equivalent."),
        ("src\\tools\\LSPTool\\LSPTool.ts", "tools/lsp", "LSP symbol search/format/refactor (6 files)", "api_server/tools/lsp.py", "analyzed",
         "MEDIUM: Python lsp.py stub exists but formatters.ts/schemas.ts/symbolContext.ts not implemented."),
        ("src\\tools\\MCPTool\\MCPTool.ts", "tools/mcp", "MCP server tools bridge with collapse classification (4 files)", "api_server/tools/mcp_tools.py", "analyzed",
         "MEDIUM: Python mcp_tools.py has limited implementation."),
        ("src\\tools\\TaskCreateTool\\TaskCreateTool.ts", "tools/tasks", "Task creation with UI (3 files)", "api_server/tools/task_tools.py", "analyzed",
         "MEDIUM: Python has basic task creation but lacks dedicated UI and constants."),
        ("src\\tools\\TeamCreateTool\\TeamCreateTool.ts", "tools/team", "Multi-agent team creation (4 files)", "api_server/tools/team_tools.py", "analyzed",
         "MEDIUM: Python team_tools.py basic implementation."),
        ("src\\tools\\SkillTool\\SkillTool.ts", "tools/skills", "Skill loading with path-based conditional activation (4 files)", "api_server/tools/skill_tool.py", "analyzed",
         "MEDIUM: Python has basic skill loading but lacks conditional activation."),
        ("src\\tools\\ScheduleCronTool\\ScheduleCronTool.ts", "tools/scheduling", "Cron job CRUD with UI (5 files)", "api_server/tools/cron_tool.py", "analyzed",
         "MEDIUM: Python cron_tool.py exists but TypeScript has 5 dedicated files with UI."),
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
