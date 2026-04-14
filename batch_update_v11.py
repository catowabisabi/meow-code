"""第十一輪分析批量更新腳本
更新 migrations, upstreamproxy, commands, hooks 模組"""
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
        # Migrations (11 files - all COMPLETE/architectural gap)
        ("src\\migrations\\migrateAutoUpdatesToSettings.ts", "migrations/settings", "Moves autoUpdates to settings.json DISABLE_AUTOUPDATER env var", "NONE", "analyzed",
         "CRITICAL: Python uses SQLite key-value; no globalConfig concept. DISABLE_AUTOUPDATER migration has no equivalent."),
        ("src\\migrations\\migrateBypassPermissionsAcceptedToSettings.ts", "migrations/permissions", "Moves bypassPermissionsModeAccepted to skipDangerousModePermissionPrompt", "NONE", "analyzed",
         "CRITICAL: Permission prompt settings are CLI-specific. Python has different security model."),
        ("src\\migrations\\migrateEnableAllProjectMcpServersToSettings.ts", "migrations/mcp", "Moves MCP server approval from projectConfig to localSettings", "NONE", "analyzed",
         "HIGH: MCP server configuration is client-side concept. Python API doesn't manage MCP approvals."),
        ("src\\migrations\\migrateFennecToOpus.ts", "migrations/model", "Migrates fennec-latest -> opus alias", "NONE", "analyzed",
         "MEDIUM: Model alias migration is CLI-specific. Python uses direct model IDs."),
        ("src\\migrations\\migrateLegacyOpusToCurrent.ts", "migrations/model", "Migrates claude-opus-4-0/4-1 -> opus alias", "NONE", "analyzed",
         "MEDIUM: CLI model alias resolution not applicable to Python API."),
        ("src\\migrations\\migrateOpusToOpus1m.ts", "migrations/model", "Migrates opus -> opus[1m] for eligible users", "NONE", "analyzed",
         "MEDIUM: CLI eligibility checks have no Python equivalent."),
        ("src\\migrations\\migrateReplBridgeEnabledToRemoteControlAtStartup.ts", "migrations/config", "Migrates replBridgeEnabled -> remoteControlAtStartup", "NONE", "analyzed",
         "LOW: REPL bridge is TypeScript/CLI concept."),
        ("src\\migrations\\migrateSonnet1mToSonnet45.ts", "migrations/model", "Migrates sonnet[1m] -> sonnet-4-5-20250929[1m]", "NONE", "analyzed",
         "MEDIUM: CLI model pinning not applicable."),
        ("src\\migrations\\migrateSonnet45ToSonnet46.ts", "migrations/model", "Migrates explicit Sonnet 4.5 -> sonnet alias", "NONE", "analyzed",
         "MEDIUM: CLI model alias resolution not applicable."),
        ("src\\migrations\\resetAutoModeOptInForDefaultOffer.ts", "migrations/ui", "Resets auto mode opt-in to re-show dialog", "NONE", "analyzed",
         "LOW: Auto mode UI flow is CLI-specific."),
        ("src\\migrations\\resetProToOpusDefault.ts", "migrations/model", "Resets Pro subscribers to Opus 4.5 default", "NONE", "analyzed",
         "MEDIUM: Pro subscriber detection is CLI-specific."),

        # Upstreamproxy (2 files - both CRITICAL)
        ("src\\upstreamproxy\\relay.ts", "upstreamproxy/relay", "TCP CONNECT -> WebSocket tunnel with UpstreamProxyChunk protobuf framing (457 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: No Python TCP server, no CONNECT parser, no protobuf encode/decode, no WebSocket binary relay, no ws-package proxy-agent integration."),
        ("src\\upstreamproxy\\upstreamproxy.ts", "upstreamproxy/init", "CCR proxy init: token lifecycle, prctl security hardening, CA bundle fetch, NO_PROXY list, subprocess env injection (285 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Zero Python coverage across 6 subsystems: token read/unlink, prctl hardening, CA bundle fetch/concat, 14-entry NO_PROXY, 8-key env map for proxy certs."),

        # Commands (key files - CRITICAL/HIGH)
        ("src\\commands\\insights.ts", "commands/insights", "Conversation insights & analytics - 3200+ lines with remote host collection, pattern detection (116KB)", "api_server/routes/commands.py (insights stub)", "analyzed",
         "CRITICAL: Python has stub analysis. TypeScript has full implementation with remote host collection, pattern detection, narrative generation."),
        ("src\\commands\\init.ts", "commands/init", "Project initialization with multi-phase wizard (21071 bytes)", "api_server/routes/commands.py (init endpoint)", "analyzed",
         "HIGH: Python has basic file creation. Missing multi-phase interactive wizard flow."),
        ("src\\commands\\memory\\index.ts", "commands/memory", "Memory management commands", "NONE", "analyzed",
         "HIGH: Memory system not implemented in Python API server."),
        ("src\\commands\\thinkback\\index.ts", "commands/thinkback", "Conversation memory review", "NONE", "analyzed",
         "HIGH: Thinkback feature not implemented."),
        ("src\\commands\\remote-setup\\index.ts", "commands/remote", "Remote setup infrastructure", "NONE", "analyzed",
         "HIGH: Remote setup not implemented."),
        ("src\\commands\\remote-setup\\api.ts", "commands/remote", "Remote setup API (5622 bytes)", "NONE", "analyzed",
         "HIGH: Remote setup API not implemented."),
        ("src\\commands\\voice\\voice.ts", "commands/voice", "Voice implementation (5358 bytes)", "NONE", "analyzed",
         "HIGH: Voice processing not implemented in Python."),
        ("src\\commands\\install-github-app\\setupGitHubActions.ts", "commands/github", "GitHub Actions setup (10275 bytes)", "NONE", "analyzed",
         "HIGH: GitHub Actions setup not implemented."),
        ("src\\commands\\advisor.ts", "commands/advisor", "AI advisor configuration (3319 bytes)", "NONE", "analyzed",
         "HIGH: Advisor configuration not implemented."),

        # Hooks (key files - NO_MATCH/HIGH)
        ("src\\hooks\\toolPermission\\PermissionContext.ts", "hooks/permissions", "Core permission state machine: logDecision, runHooks, tryClassifier, buildAllow/Deny (392 lines)", "NONE", "analyzed",
         "NO_MATCH: Deeply stateful React+IPC pattern. Python equivalent would require completely different async permission flow design."),
        ("src\\hooks\\toolPermission\\permissionLogging.ts", "hooks/telemetry", "Centralized analytics fan-out: Statsig + OTel + code-edit counters (242 lines)", "NONE", "analyzed",
         "HIGH: Python lacks unified telemetry pipeline. Gap: POST /api/v1/analytics/permission-decision."),
        ("src\\hooks\\toolPermission\\handlers\\interactiveHandler.ts", "hooks/permissions", "Interactive permission branch: 5-way race (local/hook/classifier/bridge/channel) (540 lines)", "NONE", "analyzed",
         "NO_MATCH: Most complex hook - 5-way concurrent race with no Python REST equivalent."),
        ("src\\hooks\\useCanUseTool.tsx", "hooks/permissions", "Main permission orchestrator: routes to 3 handlers + speculative pre-check (210 lines)", "NONE", "analyzed",
         "NO_MATCH: Pure TUI state machine orchestrating all permission branches."),
        ("src\\hooks\\useReplBridge.tsx", "hooks/bridge", "Always-on claude.ai bridge (BRIDGE_MODE): init/teardown, message relay, permission forwarding (728 lines)", "NONE", "analyzed",
         "HIGH CRITICAL: Python has no bridge/CCR integration. Massive gap - remote control requires WebSocket infrastructure."),
        ("src\\hooks\\useSwarmPermissionPoller.ts", "hooks/swarm", "500ms poll for swarm leader permission responses via disk mailbox (330 lines)", "NONE", "analyzed",
         "NO_MATCH: Swarm IPC via file polling. No Python equivalent."),
        ("src\\hooks\\useSSHSession.ts", "hooks/ssh", "SSH child-process session: message/permission/reconnect callbacks (241 lines)", "NONE", "analyzed",
         "HIGH: Python has no SSH session management. Gap: claude ssh equivalent."),
        ("src\\hooks\\useDirectConnect.ts", "hooks/remote", "WebSocket direct-connect session (233 lines)", "NONE", "analyzed",
         "HIGH: Python has no WebSocket direct-connect support."),
        ("src\\hooks\\fileSuggestions.ts", "hooks/autocomplete", "File path autocomplete: git ls-files + ripgrep + Rust FileIndex + untracked merge (815 lines)", "NONE", "analyzed",
         "HIGH: No fuzzy file search equivalent. Gap: POST /api/v1/suggestions/files."),
        ("src\\hooks\\unifiedSuggestions.ts", "hooks/autocomplete", "Unified @ mention suggestions: files + MCP resources + agents via Fuse.js (206 lines)", "NONE", "analyzed",
         "HIGH: No unified @ suggestion system. Gap: POST /api/v1/suggestions/unified."),
        ("src\\hooks\\usePromptsFromClaudeInChrome.tsx", "hooks/chrome", "Chrome extension prompts MCP notification handler (76 lines)", "NONE", "analyzed",
         "HIGH: Python has no Chrome extension integration. Gap: POST /api/v1/prompts/inject."),
        ("src\\hooks\\useTeleportResume.tsx", "hooks/teleport", "Teleport remote session resume (90 lines)", "NONE", "analyzed",
         "HIGH: Python has no teleport/remote session resume."),
        ("src\\hooks\\useBackgroundTaskNavigation.ts", "hooks/swarm", "Shift+Up/Down teammate tree keyboard navigation (255 lines)", "NONE", "analyzed",
         "NO_MATCH: TUI keyboard navigation for swarm UI."),
        ("src\\hooks\\useCancelRequest.ts", "hooks/input", "Escape/Ctrl+C/Ctrl+X cancel handler with two-press kill-agents (276 lines)", "NONE", "analyzed",
         "NO_MATCH: Keyboard input handling. No REST equivalent."),
        ("src\\hooks\\useSessionBackgrounding.ts", "hooks/session", "Ctrl+B session backgrounding with task sync (158 lines)", "NONE", "analyzed",
         "NO_MATCH: TUI session management. No REST equivalent."),
        ("src\\hooks\\useVirtualScroll.ts", "hooks/ui", "React-level ScrollBox virtualization: height cache, deferred values, slide cap (726 lines)", "NONE", "analyzed",
         "NO_MATCH: TUI rendering infrastructure. No REST equivalent."),
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
