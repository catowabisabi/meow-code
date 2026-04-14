"""第十輪分析批量更新腳本
更新 screens, server, schemas, plugins, native-ts, memdir, components, ink/vim 模組"""
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
        # Screens (Doctor, REPL, ResumeConversation)
        ("src\\screens\\Doctor.tsx", "screens/diagnostics", "System diagnostics UI - checks agents/MCP tools/env vars/validation errors/version locks (579 lines)", "api_server/routes/commands.py:1402", "analyzed",
         "COMPLETE: Python /doctor endpoint only checks git version. Missing: agent validation, MCP tool checks, env var validation, lock detection."),
        ("src\\screens\\REPL.tsx", "screens/interface", "Main interactive REPL screen (4750 lines) - prompt input, task execution, Ctrl+B backgrounding, history recovery", "api_server/tools/repl.py", "analyzed",
         "COMPLETE: Python REPL tool is only code execution (265 lines). Missing: full REPL UI, prompt handling, message display, task management, keybindings."),
        ("src\\screens\\ResumeConversation.tsx", "screens/session", "Conversation resume UI with LogSelector, cross-project resume, session switching (403 lines)", "api_server/routes/sessions.py + api_server/services/session_store.py", "analyzed",
         "PARTIAL: Session persistence exists but LogSelector UI, progressive log loading, PR filtering missing."),

        # Server (Direct Connect)
        ("src\\server\\createDirectConnectSession.ts", "server/direct_connect", "Creates direct connect session via HTTP POST to /sessions (93 lines)", "api_server/routes/sessions.py", "analyzed",
         "PARTIAL: TS creates direct-connect sessions (returns session_id/ws_url); Python manages chat sessions (different payload)."),
        ("src\\server\\directConnectManager.ts", "server/direct_connect", "WebSocket client for direct connect server with permission handling (217 lines)", "api_server/routes/bridge.py + api_server/ws/bridge_ws.py", "analyzed",
         "PARTIAL: TS handles SDK messages/control_requests; Python bridge.py has WebSocket but different protocol."),
        ("src\\server\\types.ts", "server/types", "DirectConnectConfig, ServerConfig, SessionInfo, SessionIndex types (61 lines)", "NONE", "analyzed",
         "NO_MATCH: Python lacks schema for direct connect response (session_id, ws_url, work_dir)."),

        # Schemas (hooks.ts - only file in schemas/)
        ("src\\schemas\\hooks.ts", "schema/hooks", "Zod schemas for hook configs: BashCommandHook, PromptHook, HttpHook, AgentHook, HookMatcher, Hooks (222 lines)", "api_server/routes/hooks.py + api_server/services/tools/hooks.py", "analyzed",
         "COMPLETE: Python lacks Pydantic schemas for hook command types, HookMatcherSchema discriminated union, HooksSchema partial record. Only has runtime ToolHooks execution."),

        # Plugins
        ("src\\plugins\\bundled\\index.ts", "plugins/builtin", "Empty scaffolding - initBuiltinPlugins() stub does nothing (23 lines)", "NONE", "analyzed",
         "COMPLETE: Built-in plugin initialization scaffolding has no Python equivalent."),
        ("src\\plugins\\builtinPlugins.ts", "plugins/builtin", "Built-in plugin registry: registerBuiltinPlugin, isBuiltinPluginId, getBuiltinPlugins (159 lines)", "NONE", "analyzed",
         "COMPLETE: Built-in plugin concept (CLI-bundled plugins with user-toggleable enable/disable) has NO Python equivalent."),
        ("src\\services\\plugins\\pluginOperations.ts", "plugins/operations", "Core plugin CRUD: install/uninstall/enable/disable/update with marketplace search, dependency resolution (1088 lines)", "api_server/services/plugins/operations.py", "analyzed",
         "PARTIAL: Python has stubs but lacks: marketplace search, findReverseDependents, loadInstalledPluginsV2, scope-aware checking."),
        ("src\\services\\plugins\\PluginInstallationManager.ts", "plugins/background", "Background marketplace reconciliation: performBackgroundPluginInstallations, diffMarketplaces (184 lines)", "NONE", "analyzed",
         "COMPLETE: Background installation manager has NO Python equivalent. Non-blocking startup flow missing."),
        ("src\\services\\plugins\\pluginCliCommands.ts", "plugins/cli", "CLI wrappers with analytics: installPlugin, uninstallPlugin with console output, process.exit (344 lines)", "api_server/services/plugins/plugin_cli_commands.py", "analyzed",
         "PARTIAL: Python CLI lacks: analytics events (tengu_plugin_*_cli), process.exit patterns, figures/console output."),
        ("src\\types\\plugin.ts", "plugins/types", "27 discriminated union PluginError types: path-not-found, git-auth-failed, network-error, etc. (368 lines)", "NONE", "analyzed",
         "COMPLETE: 27-type discriminated union error system has NO Python equivalent. TypeScript uses exhaustive switch matching."),

        # Native-ts (file-index, yoga-layout, color-diff)
        ("src\\native-ts\\file-index\\index.ts", "native-ts/index", "Fuzzy file search using nucleo/fzf-style scoring with bitmap indexing (375 lines)", "NONE", "analyzed",
         "COMPLETE: No fuzzy file search equivalent. api_server has no file indexing capability."),
        ("src\\native-ts\\color-diff\\index.ts", "native-ts/color", "Syntax highlighting via highlight.js + diffArrays word diff (1004 lines)", "NONE", "analyzed",
         "COMPLETE: No syntax highlighting or diff rendering. services/tools_service.py returns raw text."),
        ("src\\native-ts\\yoga-layout\\index.ts", "native-ts/layout", "Pure-TS flexbox engine (Meta's yoga-layout port) with multi-pass layout cache (1800+ lines)", "NONE", "analyzed",
         "COMPLETE: No layout engine. webui uses React/CSS; this is CLI-specific."),
        ("src\\native-ts\\yoga-layout\\enums.ts", "native-ts/layout", "Yoga enums: Align, FlexDirection, JustifyContent, Gutter, etc. (139 lines)", "NONE", "analyzed",
         "COMPLETE: Python equivalent not needed (TS-specific layout constants)."),

        # Memdir (memory system)
        ("src\\memdir\\memdir.ts", "memdir/core", "Core memory: MEMORY.md truncation, prompt building, KAIROS daily-log mode (512 lines)", "api_server/services/memory.py", "analyzed",
         "PARTIAL: Python memory.py lacks: prompt building, truncation logic, KAIROS mode, loadMemoryPrompt dispatcher."),
        ("src\\memdir\\memoryTypes.ts", "memdir/types", "Memory taxonomy: user/feedback/project/reference types with scope guidance (271 lines)", "NONE", "analyzed",
         "COMPLETE: No Python equivalent. extract_memories.py uses different types (fact/decision/preference/context)."),
        ("src\\memdir\\memoryScan.ts", "memdir/scan", "scanMemoryFiles() recursive readdir, frontmatter parse, mtime sort (94 lines)", "api_server/services/memory.py", "analyzed",
         "PARTIAL: Python list_memories() lacks async scanning, frontmatter parsing, mtime-based sorting."),
        ("src\\memdir\\memoryAge.ts", "memdir/age", "Memory age utilities: memoryAgeDays(), memoryFreshnessText() for staleness (58 lines)", "NONE", "analyzed",
         "COMPLETE: No Python staleness warnings. No memory age tracking in api_server."),
        ("src\\memdir\\paths.ts", "memdir/paths", "Auto-memory path resolution: getAutoMemPath(), isAutoMemoryEnabled(), ~/ expansion (283 lines)", "api_server/agents/tool/memory.py", "analyzed",
         "PARTIAL: Python has get_agent_memory_dir() but lacks KAIROS daily-log, feature flag gating."),
        ("src\\memdir\\teamMemPaths.ts", "memdir/team", "Team memory path validation: symlink resolution, PathTraversalError, validateTeamMemWritePath (296 lines)", "api_server/services/team_memory_sync.py", "analyzed",
         "PARTIAL: team_memory_sync.py handles sync but lacks path validation and symlink security checks."),
        ("src\\memdir\\teamMemPrompts.ts", "memdir/team", "buildCombinedMemoryPrompt() for auto+team mode with TYPES_SECTION_COMBINED (105 lines)", "api_server/services/team_memory_sync.py", "analyzed",
         "PARTIAL: team_memory_sync.py handles sync but lacks prompt building with combined scope guidance."),
        ("src\\memdir\\findRelevantMemories.ts", "memdir/search", "Find relevant memories using LLM (Sonnet) selection - top 5 relevant (146 lines)", "NONE", "analyzed",
         "COMPLETE: No AI-powered memory relevance selection. Python has no equivalent."),

        # Components (UI - 143 files, all COMPLETE)
        ("src\\components\\App.tsx", "components/app", "Root application shell, mounts all panels", "NONE", "analyzed",
         "COMPLETE: No Python UI shell. api_server is HTTP server only."),
        ("src\\components\\Message.tsx", "components/messages", "Core message display component", "NONE", "analyzed",
         "COMPLETE: No Python message rendering."),
        ("src\\components\\PromptInput\\PromptInput.tsx", "components/prompt", "Main prompt input component", "NONE", "analyzed",
         "COMPLETE: No Python prompt input component."),
        ("src\\components\\Settings\\Settings.tsx", "components/settings", "Main settings screen", "api_server/routes/settings.py", "analyzed",
         "COMPLETE: Settings route stores config; no settings UI."),
        ("src\\components\\tasks\\BackgroundTasksDialog.tsx", "components/tasks", "Dialog listing all background tasks", "api_server/routes/sessions.py", "analyzed",
         "COMPLETE: Session data exists; no background task dialog."),

        # Ink/Vim (TUI engine - 102 files)
        ("src\\ink\\ink.tsx", "ink/core", "Main Ink class: alt-screen, mouse tracking, frame double-buffering, SIGCONT/resize (1200+ lines)", "NONE", "analyzed",
         "COMPLETE: FastAPI is REST server with no terminal rendering. Zero equivalent."),
        ("src\\ink\\reconciler.ts", "ink/core", "Custom React reconciler: createContainer, commitUpdate, yoga lifecycle (516 lines)", "NONE", "analyzed",
         "COMPLETE: Python has no React-like tree reconciliation."),
        ("src\\ink\\screen.ts", "ink/core", "Packed typed-array screen buffer: CharPool, StylePool, blitRegion, diffEach (1490 lines)", "NONE", "analyzed",
         "COMPLETE: Terminal buffer system. Python server sends JSON, not cell buffers."),
        ("src\\ink\\log-update.ts", "ink/core", "Diff engine: prev frame -> next frame -> minimal patch sequence (777 lines)", "NONE", "analyzed",
         "COMPLETE: No incremental terminal diff concept."),
        ("src\\ink\\parse-keypress.ts", "ink/input", "Raw stdin parser: VT100/Kitty/xterm key sequences, SGR mouse (740 lines)", "NONE", "analyzed",
         "COMPLETE: Python API reads HTTP/WebSocket, not raw stdin bytes."),
        ("src\\ink\\styles.ts", "ink/styling", "Terminal CSS: color/bold/italic/underline types, ANSI code builders (660 lines)", "NONE", "analyzed",
         "COMPLETE: Styling is terminal-native. No HTTP API equivalent."),
        ("src\\ink\\components\\App.tsx", "ink/components", "Root React component: raw mode, stdin event loop, mouse tracking (662 lines)", "NONE", "analyzed",
         "COMPLETE: Entire terminal lifecycle. No Python equivalent."),
        ("src\\ink\\components\\Box.tsx", "ink/components", "Flexbox layout container: maps style props to Yoga attributes (217 lines)", "NONE", "analyzed",
         "COMPLETE: Terminal layout box. API sends JSON, not layout boxes."),
        ("src\\ink\\components\\Text.tsx", "ink/components", "Styled text renderer: color, bold, italic, underline, wrap (258 lines)", "NONE", "analyzed",
         "COMPLETE: No terminal text rendering in Python."),
        ("src\\ink\\termio\\csi.ts", "ink/termio", "CSI sequences: cursor movement, scroll region, erase, kitty keyboard (261 lines)", "NONE", "analyzed",
         "COMPLETE: Python server does not emit terminal escape sequences."),
        ("src\\ink\\termio\\osc.ts", "ink/termio", "OSC sequences: hyperlinks (OSC 8), clipboard (OSC 52), tab status (452 lines)", "NONE", "analyzed",
         "COMPLETE: No OSC protocol in Python API server."),
        ("src\\ink\\termio\\parser.ts", "ink/termio", "State-machine parser for raw stdin escape sequences (348 lines)", "NONE", "analyzed",
         "COMPLETE: No terminal protocol parsing."),
        ("src\\ink\\layout\\yoga.ts", "ink/layout", "Yoga WASM wrapper: FlexDirection, AlignItems, JustifyContent (270 lines)", "NONE", "analyzed",
         "COMPLETE: Flexbox layout engine. No Python equivalent."),
        ("src\\vim\\types.ts", "vim/core", "Vim state machine types: VimState, CommandState, PersistentState (205 lines)", "NONE", "analyzed",
         "COMPLETE: No vim mode keybinding state machine."),
        ("src\\vim\\transitions.ts", "vim/core", "Vim state transition table: input -> next state/execute action (496 lines)", "NONE", "analyzed",
         "COMPLETE: No terminal input state machine."),
        ("src\\vim\\operators.ts", "vim/core", "Vim operator executors: delete/change/yank/x/r/J/paste (561 lines)", "NONE", "analyzed",
         "COMPLETE: No vim operator system."),
        ("src\\vim\\textObjects.ts", "vim/core", "Text object boundary finders: iw/aw, i\"/a\", i(/a( (191 lines)", "NONE", "analyzed",
         "COMPLETE: No text object system."),
        ("src\\outputStyles\\loadOutputStylesDir.ts", "outputstyles", "Loads ~/.claude/output-styles/*.md -> OutputStyleConfig[] (103 lines)", "api_server/services/", "analyzed",
         "PARTIAL: Python may load styles from config but not filesystem markdown with frontmatter."),
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
