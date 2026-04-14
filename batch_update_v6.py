"""第六輪分析批量更新腳本
更新 ide, terminal, services, commands, native-ts, memdir, migrations, voice 模組"""
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
        # IDE Module
        ("src\\utils\\ide.ts", "ide/detection", "IDE detection (lockfiles+process), VS Code/Cursor/Windsurf/JetBrains, extension install, auto-connect", "MISSING", "analyzed",
         "CRITICAL: detectIDEs/findAvailableIDE/cleanupStaleIdeLockfiles/isIDEExtensionInstalled MISSING"),
        ("src\\commands\\ide\\ide.tsx", "ide/command", "IDE command with open subcommand, selection UI, connection management", "MISSING", "analyzed",
         "CRITICAL: /ide CLI command MISSING - no auto-connect dialog, onboarding"),
        ("src\\components\\IdeAutoConnectDialog.tsx", "ide/ui", "Auto-connect confirmation dialog", "MISSING", "analyzed",
         "CRITICAL: Auto-connect dialog UI MISSING"),
        ("src\\components\\IdeOnboardingDialog.tsx", "ide/ui", "IDE onboarding/welcome dialog", "MISSING", "analyzed",
         "CRITICAL: Onboarding dialog UI MISSING"),
        ("src\\hooks\\useIDEIntegration.tsx", "ide/hooks", "IDE integration hook for auto-connect, extension status", "MISSING", "analyzed",
         "CRITICAL: useIDEIntegration hook MISSING"),
        ("src\\utils\\idePathConversion.ts", "ide/path", "WSL/Windows path conversion", "MISSING", "analyzed",
         "GAPS: idePathConversion MISSING - no cross-platform path handling"),
        ("src\\services\\mcp\\client.ts", "ide/mcp-client", "MCP client with IDE notification (maybeNotifyIDEConnected, sse-ide/ws-ide)", "services/mcp/client.py (partial)", "analyzed",
         "GAPS: SSE-IDE/WS-IDE transport types MISSING, IDE notification MISSING"),

        # Terminal Module
        ("src\\ink\\terminal.ts", "terminal/detection", "OSC 9;4 progress, DEC 2026 sync output, XTVERSION terminal detection", "MISSING", "analyzed",
         "CRITICAL: OSC 9;4/DEC 2026/XTVERSION detection MISSING"),
        ("src\\ink\\terminal-focus-state.ts", "terminal/focus", "DECSET 1004 focus tracking (focused/blurred/unknown)", "MISSING", "analyzed",
         "CRITICAL: Terminal focus state tracking MISSING"),
        ("src\\ink\\terminal-querier.ts", "terminal/querier", "Terminal capability queries (DECRQM, DA1/DA2, kittyKeyboard, XTVERSION)", "MISSING", "analyzed",
         "CRITICAL: Terminal querier system MISSING"),
        ("src\\ink\\termio\\csi.ts", "terminal/csi", "CSI commands (cursor move, erase, scroll, SGR, mode set)", "MISSING", "analyzed",
         "CRITICAL: ANSI CSI sequence generation MISSING"),
        ("src\\ink\\termio\\dec.ts", "terminal/dec", "DEC private modes (sync output 2026, focus 1004, paste 2004, mouse 1006)", "MISSING", "analyzed",
         "CRITICAL: DEC private modes MISSING"),
        ("src\\ink\\termio\\osc.ts", "terminal/osc", "OSC commands (title, hyperlinks 8, clipboard 52, iTerm2 9, Ghostty 777)", "MISSING", "analyzed",
         "CRITICAL: OSC hyperlink/clipboard/title MISSING"),
        ("src\\ink\\termio\\tokenize.ts", "terminal/tokenizer", "ANSI escape sequence tokenizer", "MISSING", "analyzed",
         "CRITICAL: ANSI tokenizer MISSING"),
        ("src\\ink\\parse-keypress.ts", "terminal/input", "Kitty keyboard protocol, SGR mouse, bracketed paste parsing", "MISSING", "analyzed",
         "CRITICAL: Keyboard/mouse event parsing MISSING"),
        ("src\\utils\\terminal.ts", "terminal/render", "ANSI-aware terminal text truncation/wrapping", "MISSING", "analyzed",
         "CRITICAL: ANSI-aware text rendering MISSING"),
        ("src\\utils\\terminalPanel.ts", "terminal/panel", "Built-in tmux terminal panel (Meta+J)", "agents/teammate/tmux_backend.py (partial)", "analyzed",
         "GAPS: tmux_backend has basic pane ops, no terminal capability detection"),

        # Services Module
        ("src\\services\\analytics\\index.ts", "services/analytics", "Analytics sink routing, queueing, Datadog integration, event sampling", "services/analytics.py (partial)", "analyzed",
         "GAPS: Python has log_event, missing Datadog sink, event sampling, GrowthBook integration"),
        ("src\\services\\mcp\\client.ts", "services/mcp-client", "Full MCP client (2400+ lines): SSE/HTTP/WS/stdio/OAuth, session expiry, auth cache", "services/mcp/client.py (partial)", "analyzed",
         "MAJOR: WS transport/OAuth auth provider/session expiry/Claude.ai proxy MISSING"),
        ("src\\services\\plugins\\pluginOperations.ts", "services/plugins", "Plugin lifecycle (1088 lines): install/uninstall/enable/disable, scope resolution, dependency", "plugins/manager.py (partial)", "analyzed",
         "MAJOR: Full lifecycle with marketplace/scope/dependency MISSING"),
        ("src\\services\\remoteManagedSettings\\index.ts", "services/remote-settings", "Remote managed settings (638 lines): polling, ETag, security checks, background refresh", "MISSING", "analyzed",
         "CRITICAL: Remote managed settings MISSING"),
        ("src\\services\\compact\\microCompact.ts", "services/compact", "Cached microcompact (535 lines): cache_edits API, time-based triggers, token estimation", "MISSING", "analyzed",
         "CRITICAL: Cached microcompact with cache_edits MISSING"),
        ("src\\services\\teamMemorySync\\index.ts", "services/team-memory", "Team memory sync (1256 lines): delta upload, conflict resolution, secret scanning", "services/team_memory_sync/ (partial)", "analyzed",
         "MAJOR: Delta upload/conflict resolution/secret scanning MISSING"),
        ("src\\services\\SessionMemory\\sessionMemory.ts", "services/session-memory", "Forked agent session memory extraction", "services/session_memory/memory.py (partial)", "analyzed",
         "GAPS: Forked agent pattern MISSING"),
        ("src\\services\\extractMemories\\extractMemories.ts", "services/extract-memories", "Forked agent memory extraction with tool constraints", "MISSING", "analyzed",
         "CRITICAL: Forked agent pattern MISSING"),
        ("src\\services\\autoDream\\autoDream.ts", "services/auto-dream", "Background dream consolidation with time/session gates, locking", "MISSING", "analyzed",
         "CRITICAL: Time/session gates and consolidation locking MISSING"),
        ("src\\services\\lsp\\passiveFeedback.ts", "services/lsp-feedback", "LSP passive diagnostics feedback", "services/lsp/passive_feedback.py", "analyzed",
         "PARITY: Python has passive_feedback.py"),
        ("src\\services\\settingsSync\\index.ts", "services/settings-sync", "Settings sync with delta upload, download, cache management", "MISSING", "analyzed",
         "CRITICAL: Delta upload/settings sync MISSING"),
        ("src\\services\\oauth\\client.ts", "services/oauth", "Full OAuth PKCE flow (token refresh, profile fetch, step-up detection)", "routes/oauth.py (partial)", "analyzed",
         "GAPS: Step-up detection/scope expansion/API key creation MISSING"),
        ("src\\services\\diagnosticTracking.ts", "services/diagnostics", "IDE diagnostic tracking with baseline comparison", "services/diagnostic_tracking.py (partial)", "analyzed",
         "GAPS: IDE RPC integration/baseline comparison MISSING"),

        # Commands Module
        ("src\\commands\\insights\\insights.ts", "commands/insights", "Insights command (1500+ lines): session analytics, AI facet extraction, multi-section reports", "routes/commands.py (STUB)", "analyzed",
         "CRITICAL: Python returns hardcoded patterns only - no AI facet extraction"),
        ("src\\commands\\thinkback\\thinkback.ts", "commands/thinkback", "Thinkback command: plugin install, skill loading, animation playback", "MISSING", "analyzed",
         "CRITICAL: Thinkback command MISSING"),
        ("src\\commands\\branch\\branch.ts", "commands/branch", "Branch command: session fork with metadata preservation, fork traceability", "MISSING", "analyzed",
         "CRITICAL: Branch/fork command MISSING"),
        ("src\\commands\\memory\\memory.ts", "commands/memory", "Memory command: file selector, editor integration, memory file management", "MISSING", "analyzed",
         "CRITICAL: Memory command CLI MISSING"),
        ("src\\commands\\login\\login.ts", "commands/login", "Login command: OAuth flow, trusted device enrollment, cache clearing", "MISSING", "analyzed",
         "CRITICAL: Login/logout commands MISSING"),
        ("src\\commands\\privacy-settings\\privacy-settings.ts", "commands/privacy", "Privacy settings: Grove integration, analytics tracking", "MISSING", "analyzed",
         "CRITICAL: Privacy settings command MISSING"),
        ("src\\commands\\init\\init.ts", "commands/init", "Init command (260+ lines): multi-phase interactive project setup, subagent spawning", "routes/commands.py (STUB)", "analyzed",
         "GAPS: Python only creates basic CLAUDE.md template"),
        ("src\\commands\\tasks\\tasks.ts", "commands/tasks", "Tasks command: React dialog-based task management", "MISSING", "analyzed",
         "CRITICAL: Tasks UI dialog MISSING"),
        ("src\\commands\\compact\\compact.ts", "commands/compact", "Compact command: AI summarization service", "routes/commands.py (partial)", "analyzed",
         "GAPS: Python has basic truncation only"),

        # Native-TS Module
        ("src\\native-ts\\color-diff\\index.ts", "native-ts/color-diff", "Syntax highlighting + word-level diff using highlight.js (1004 lines)", "MISSING", "analyzed",
         "NOTE: CLI diff rendering - not needed for API server"),
        ("src\\native-ts\\file-index\\index.ts", "native-ts/file-index", "Fuzzy file search (nucleo/fzf-style) with boundary/camel/consecutive scoring (375 lines)", "MISSING", "analyzed",
         "CRITICAL: No nucleo/fzf-style fuzzy path search - Python only has ripgrep content search"),
        ("src\\native-ts\\yoga-layout\\index.ts", "native-ts/yoga", "Flexbox layout engine (Meta yoga-layout) for terminal UI (1620+ lines)", "N/A", "analyzed",
         "N/A: UI layout engine - irrelevant for Python API server"),

        # Memdir Module
        ("src\\memdir\\memdir.ts", "memdir/core", "Core memory prompt builder: truncateEntrypointContent, buildMemoryLines, loadMemoryPrompt", "services/memory.py (partial)", "analyzed",
         "CRITICAL: truncateEntrypointContent MISSING - Python reads as-is, no token cap"),
        ("src\\memdir\\memoryTypes.ts", "memdir/types", "Memory taxonomy (user/feedback/project/reference), rich prompt copy, drift caveats", "services/memory.py (partial)", "analyzed",
         "CRITICAL: Memory type prompt injection MISSING"),
        ("src\\memdir\\paths.ts", "memdir/paths", "Multi-priority path resolution, security validation, feature gates (CLAUDE_COWORK_MEMORY_PATH_OVERRIDE)", "MISSING", "analyzed",
         "CRITICAL: Security path validation and multi-priority override MISSING"),
        ("src\\memdir\\memoryAge.ts", "memdir/age", "Memory staleness calculation, freshness warning text", "MISSING", "analyzed",
         "CRITICAL: Memory age/staleness tracking entirely MISSING"),
        ("src\\memdir\\memoryScan.ts", "memdir/scan", "Recursive .md scanner, frontmatter parsing, newest-first sort, 200-file cap", "services/memory.py (partial)", "analyzed",
         "CRITICAL: Python uses flat glob - no recursion/frontmatter/cap"),
        ("src\\memdir\\findRelevantMemories.ts", "memdir/ai-search", "AI-powered (Sonnet) semantic relevance recall, up to 5 relevant files per query", "services/memory.py (keyword only)", "analyzed",
         "CRITICAL: Python uses dumb substring match - no AI ranking"),
        ("src\\memdir\\teamMemPaths.ts", "memdir/team-paths", "Team memory path security: symlink traversal defense, sanitizePathKey, validateTeamMemWritePath", "services/team_memory_sync/ (partial)", "analyzed",
         "CRITICAL: Symlink escape protection MISSING in Python sync"),
        ("src\\memdir\\teamMemPrompts.ts", "memdir/team-prompts", "Combined auto+team memory prompt builder", "MISSING", "analyzed",
         "CRITICAL: Combined team+auto prompt MISSING"),

        # Migrations Module
        ("src\\migrations\\", "migrations/core", "Migration system: 11 migrations (model alias, settings, config key, reset)", "MISSING", "analyzed",
         "CRITICAL: Migration system completely MISSING in Python"),
        ("src\\utils\\settings\\settings.ts", "migrations/settings", "Multi-source settings system: user/local/project/policy/flag sources with Zod validation", "db/settings_db.py (flat)", "analyzed",
         "CRITICAL: Multi-source settings and Zod validation MISSING"),

        # Voice Module
        ("src\\voice\\voiceModeEnabled.ts", "voice/mode", "Voice mode enable/disable checks (GrowthBook flag + OAuth)", "MISSING", "analyzed",
         "CRITICAL: Voice mode feature gate MISSING"),
        ("src\\services\\voiceStreamSTT.ts", "voice/stt", "WebSocket STT client (Anthropic voice_stream endpoint, interim transcript, auto-retry)", "MISSING", "analyzed",
         "CRITICAL: WebSocket STT completely MISSING"),
        ("src\\services\\voiceKeyterms.ts", "voice/keyterms", "STT keyword optimization (Deepgram keywords boosting: project name, branch, files)", "MISSING", "analyzed",
         "CRITICAL: Voice keyterms MISSING"),
        ("src\\services\\voice.ts", "voice/recording", "Audio recording (native cpal + SoX/arecord fallback), mic permission check", "services/voice.py (STUB)", "analyzed",
         "CRITICAL: voice.py is stub - native functions return False"),
        ("src\\hooks\\useVoice.ts", "voice/hook", "React hold-to-talk hook: volume monitoring, focus mode, session generation, analytics", "MISSING", "analyzed",
         "CRITICAL: useVoice hook MISSING - hold-to-talk UI not implemented"),
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
