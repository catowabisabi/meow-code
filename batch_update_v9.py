"""第九輪分析批量更新腳本
更新 assistant, bridge, dialogLaunchers, query, context 模組"""
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
        # Dialog Launchers (Round 9 - dialogLaunchers)
        ("src\\dialogLaunchers.tsx", "UI/Dialog", "7 specific dialog launchers: SnapshotUpdate, InvalidSettings, AssistantSession, AssistantInstall, TeleportResume, TeleportRepoMismatch, ResumeChooser", "api_server/tools/ask_user_tool.py", "analyzed",
         "NO_MATCH: Python has ask_user tool but lacks ALL 7 specific dialog launchers. No Ink-based TUI rendering framework."),
        ("src\\interactiveHelpers.tsx", "UI/Dialog", "Core TUI helpers: showDialog, showSetupDialog, renderAndRun, showSetupScreens (onboarding, trust, MCP approvals)", "api_server/ws/chat.py, api_server/services/mcp/elicitation_handler.py", "analyzed",
         "PARTIAL: Python has permission handling via WebSocket but lacks Ink TUI rendering. showSetupScreens (trust/onboarding/MCP) has no Python equivalent."),

        # Query Module (Round 9 - query/)
        ("src\\query\\config.ts", "configuration", "Immutable config snapshot with runtime gates (streamingToolExecution, emitToolUseSummaries, isAnt, fastModeEnabled)", "NONE", "analyzed",
         "NO_MATCH: Python lacks equivalent runtime gate snapshot pattern. Gates are checked inline rather than snapshotted at query() entry."),
        ("src\\query\\deps.ts", "dependency_injection", "I/O dependency interface for query() enabling test injection (callModel, microcompact, autocompact, uuid factory)", "api_server/services/compact/auto_compact.py, api_server/services/compact/micro_compact.py", "analyzed",
         "PARTIAL: Python has autocompact and microcompact functions but NOT the dependency injection pattern for testability. Python tests use monkey-patching."),
        ("src\\query\\stopHooks.ts", "hooks", "Complex async generator handling stop conditions, message tombstones, task completed hooks, teammate idle hooks (~480 lines)", "api_server/services/tools/tool_execution.py", "analyzed",
         "PARTIAL: Python has stop hook infrastructure (create_stop_hook_summary_message) but lacks comprehensive handleStopHooks pattern with async generator, tombstones, teammate hook chaining."),
        ("src\\query\\tokenBudget.ts", "token_management", "Token budget tracker with BudgetTracker, continuationCount, diminishing returns detection, checkTokenBudget()", "api_server/services/compact/", "analyzed",
         "PARTIAL: Python has token estimation and auto-compaction triggers but NOT explicit BudgetTracker structure with diminishing returns detection."),

        # Bridge Module (Round 9 - bridge/) - 31 files, mostly NO_MATCH
        ("src\\bridge\\jwtUtils.ts", "bridge/auth", "JWT decoding + proactive token refresh scheduler with retry/failure tracking (265 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python lacks proactive JWT refresh scheduler. session_ingress.py has basic token handling but no decodeJwtPayload/scheduleFromExpiresIn."),
        ("src\\bridge\\bridgeApi.ts", "bridge/api", "Full API client: registerEnvironment, pollForWork, acknowledgeWork, stopWork, heartbeatWork, deregister, archiveSession (559 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python routes/bridge.py is a stub (ping/pong only). No environment registration, work polling, or session lifecycle."),
        ("src\\bridge\\types.ts", "bridge/types", "BridgeConfig, BridgeApiClient, SessionHandle, SessionSpawner, BridgeLogger interfaces (266 lines)", "NONE", "analyzed",
         "PARTIAL: Some types mirrored in Python BridgeState, but SessionSpawner/BridgeLogger have no equivalent."),
        ("src\\bridge\\bridgeMain.ts", "bridge/core", "Standalone bridge main loop with multi-session (worktree/same-dir), backoff, reconnect, CCR v2 support (3009 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python has no standalone bridge daemon equivalent."),
        ("src\\bridge\\bridgeMessaging.ts", "bridge/messaging", "Ingress message parsing, control_request handling, echo dedup (BoundedUUIDSet), message normalization (461 lines)", "NONE", "analyzed",
         "NO_MATCH: Python lacks SDK message parsing, control request handling, UUID dedup."),
        ("src\\bridge\\bridgeUI.ts", "bridge/ui", "Terminal UI: QR code, spinner, shimmer animation, multi-session list, status line (540 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no terminal UI capabilities."),
        ("src\\bridge\\bridgeEnabled.ts", "bridge/config", "Feature gating: isBridgeEnabled, isEnvLessBridgeEnabled, GrowthBook checks (203 lines)", "NONE", "analyzed",
         "PARTIAL: Python has basic GrowthBook client but not bridge-specific gating."),
        ("src\\bridge\\bridgePointer.ts", "bridge/recovery", "Crash-recovery pointer with TTL, worktree-aware scanning (216 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no crash-recovery pointer mechanism."),
        ("src\\bridge\\createSession.ts", "bridge/api", "Session CRUD: createBridgeSession, getBridgeSession, archiveBridgeSession, updateBridgeSessionTitle (394 lines)", "NONE", "analyzed",
         "NO_MATCH: Python routes/sessions.py lacks bridge-specific session creation with git context."),
        ("src\\bridge\\replBridge.ts", "bridge/core", "REPL bridge core: v1 (HybridTransport) + v2 (SSE+CCRClient), initBridgeCore (2410 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python has no REPL bridge equivalent."),
        ("src\\bridge\\replBridgeTransport.ts", "bridge/transport", "v1 adapter (HybridTransport) + v2 adapter (SSE+CCRClient) (379 lines)", "NONE", "analyzed",
         "NO_MATCH: Python lacks SSE/WebSocket transport adapters."),
        ("src\\bridge\\remoteBridgeCore.ts", "bridge/core", "Env-less bridge: direct session-ingress connection, token refresh (1010 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no env-less bridge path."),
        ("src\\bridge\\initReplBridge.ts", "bridge/init", "REPL bridge initialization wrapper with OAuth, policy, version checks (569 lines)", "NONE", "analyzed",
         "NO_MATCH: Python lacks bridge initialization flow."),
        ("src\\bridge\\sessionRunner.ts", "bridge/runtime", "Child process spawning, stdin/stdout/stderr piping, NDJSON parsing, activity tracking (560 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no child process session spawning equivalent."),
        ("src\\bridge\\workSecret.ts", "bridge/security", "Work secret decode, SDK URL building, session ID comparison, worker registration (138 lines)", "NONE", "analyzed",
         "NO_MATCH: Python lacks work secret decoding/version validation."),
        ("src\\bridge\\trustedDevice.ts", "bridge/auth", "Trusted device enrollment, token persistence, keychain storage (219 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no trusted device flow (OAuth service has different pattern)."),
        ("src\\bridge\\envLessBridgeConfig.ts", "bridge/config", "CCR v2 timing config: retry, heartbeat, UUID dedup, JWT buffer (177 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no GrowthBook-driven config for bridge timing."),
        ("src\\bridge\\pollConfig.ts", "bridge/config", "Poll interval config from GrowthBook (poll_interval_ms, reclaim_older_than_ms) (117 lines)", "NONE", "analyzed",
         "NO_MATCH: Python lacks dynamic poll interval configuration."),
        ("src\\bridge\\pollConfigDefaults.ts", "bridge/config", "Default poll intervals (2s seeking, 10min at-capacity, 120s keepalive) (82 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no equivalent polling configuration."),
        ("src\\bridge\\bridgeConfig.ts", "bridge/config", "OAuth token/base URL retrieval with ant-only overrides (63 lines)", "NONE", "analyzed",
         "PARTIAL: Python services/api/client.py has basic token retrieval but no override pattern."),
        ("src\\bridge\\bridgeDebug.ts", "bridge/debug", "Fault injection for poll/register/reconnect/heartbeat (ANT-only) (141 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no fault injection framework for bridge."),
        ("src\\bridge\\bridgeStatusUtil.ts", "bridge/ui", "URL building, shimmer animation segments, footer text (172 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no terminal UI animation utilities."),
        ("src\\bridge\\bridgePermissionCallbacks.ts", "bridge/auth", "Permission request/response callback interfaces (47 lines)", "NONE", "analyzed",
         "NO_MATCH: Python lacks bridge permission callback types."),
        ("src\\bridge\\codeSessionApi.ts", "bridge/api", "Thin wrappers: createCodeSession, fetchRemoteCredentials (CCR v2) (168 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no CCR v2 session API wrappers."),
        ("src\\bridge\\debugUtils.ts", "bridge/debug", "Secret redaction, message truncation, axios error extraction (152 lines)", "NONE", "analyzed",
         "PARTIAL: Python tools/powershell_security.py has some redaction but not comprehensive."),
        ("src\\bridge\\capacityWake.ts", "bridge/concurrency", "AbortSignal-based wake controller for poll loops (56 lines)", "NONE", "analyzed",
         "NO_MATCH: Python asyncio lacks AbortSignal equivalent."),
        ("src\\bridge\\flushGate.ts", "bridge/messaging", "Message flush gating state machine (start/enqueue/end/drop) (71 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no equivalent flush gate."),
        ("src\\bridge\\inboundAttachments.ts", "bridge/messaging", "File UUID attachment resolution, @path ref prepending (175 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no file attachment resolution for bridge messages."),
        ("src\\bridge\\inboundMessages.ts", "bridge/messaging", "Inbound user message extraction, image block normalization (88 lines)", "NONE", "analyzed",
         "NO_MATCH: Python lacks inbound message content extraction."),
        ("src\\bridge\\sessionIdCompat.ts", "bridge/compat", "cse_/session_ ID tag translation for CCR v2 compat layer (57 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no session ID compatibility layer."),
        ("src\\bridge\\replBridgeHandle.ts", "bridge/state", "Global bridge handle reference for React tree external access (42 lines)", "NONE", "analyzed",
         "NO_MATCH: Python has no global bridge handle concept."),
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
