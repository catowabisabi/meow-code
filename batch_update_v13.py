"""第十三輪分析批量更新腳本
更新 sandbox, prompts, services, ide 模組"""
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
        # Sandbox module
        ("src\\utils\\sandbox\\sandbox-adapter.ts", "sandbox/core", "Wrapper for @anthropic-ai/sandbox-runtime: CC-specific path resolution, worktree detection, platform allowlist, refreshConfig (990 lines)", "api_server/sandbox/sandboxed_shell.py", "analyzed",
         "CRITICAL: bareGitRepoScrubPaths security feature missing. HIGH: getSandboxUnavailableReason (detailed hints), detectWorktreeMainRepoPath, isPlatformInEnabledList, resolvePathPatternForSandbox, refreshConfig."),
        ("src\\utils\\sandbox\\sandbox-ui-utils.ts", "sandbox/ui", "Remove <sandbox_violations> tags from text for UI display (17 lines)", "NONE", "analyzed",
         "LOW: No Python equivalent - UI tag removal not needed in API server."),
        ("src\\commands\\sandbox-toggle\\index.ts", "sandbox/cli", "/sandbox CLI command for sandbox configuration (54 lines)", "NONE", "analyzed",
         "LOW: CLI command for sandbox toggle - Python has sandboxed_shell.py but no user-facing command."),

        # IDE module
        ("src\\commands\\ide\\ide.tsx", "ide/integration", "IDE integration: detectIDEs, IDE selection UI (IDEScreen/IDEOpenSelection/RunningIDESelector), connection management for sse-ide/ws-ide (650 lines)", "NONE", "analyzed",
         "CRITICAL: No Python equivalent for IDE detection/selection UI. Python has MCP types for sse-ide/ws-ide but not dynamic IDE connection management."),
        ("src\\commands\\ide\\index.ts", "ide/cli", "IDE command loader (15 lines)", "NONE", "analyzed",
         "LOW: CLI command entry point."),

        # Prompts module
        ("src\\constants\\prompts.ts", "prompts/system", "Main system prompt generation with 20+ sections: intro, tasks, actions, tools, tone, proactive/kairos mode, coordinator mode (918 lines)", "api_server/prompts/builder.py", "analyzed",
         "CRITICAL: Proactive/Kairos Mode (~60 lines) completely missing. Coordinator Mode missing. ~20% coverage - Python lacks most feature-gated sections."),
        ("src\\constants\\systemPromptSections.ts", "prompts/cache", "Caching system for dynamic prompt sections with memoization (73 lines)", "api_server/prompts/cache.py", "analyzed",
         "LOW: Basic section cache exists in Python."),
        ("src\\utils\\systemPrompt.ts", "prompts/builder", "Builds effective prompt based on mode: override/coordinator/agent/custom/default (129 lines)", "api_server/prompts/builder.py", "analyzed",
         "HIGH: Missing Coordinator mode branch, fork subagent mode, proactive mode."),
        ("src\\services\\SessionMemory\\prompts.ts", "prompts/memory", "Session memory prompts: update template with section size management (329 lines)", "api_server/services/session_memory/prompts.py", "analyzed",
         "MEDIUM: Missing buildExtractAutoOnlyPrompt/combined prompts, team memory support, 4-type taxonomy."),
        ("src\\services\\extractMemories\\prompts.ts", "prompts/memory", "Background agent prompts for auto memory extraction (154 lines)", "NONE", "analyzed",
         "HIGH: Different architecture - Python uses MemoryExtractor not fork-based prompts."),
        ("src\\services\\compact\\prompt.ts", "prompts/compact", "Compaction prompts: 3 variants (BASE/PARTIAL/PARTIAL_UP_TO) + formatting + continuation (379 lines)", "api_server/services/compact/prompt.py", "analyzed",
         "LOW: Mostly complete, missing proactive continuation text."),
        ("src\\tools\\AgentTool\\prompt.ts", "prompts/agent", "Agent spawning guidance + fork semantics + examples (291 lines)", "api_server/agents/tool/built-in/general_purpose.py", "analyzed",
         "HIGH: Missing fork subagent logic, whenToForkSection, writingThePromptSection, background task guidance."),
        ("src\\buddy\\prompt.ts", "prompts/companion", "Companion intro text and attachment generation (40 lines)", "NONE", "analyzed",
         "MEDIUM: Companion system (pet AI assistant) not implemented in Python."),

        # Services module (HIGH priority items)
        ("src\\services\\teamMemorySync\\index.ts", "services/team", "Bidirectional sync: team memory <-> server API with OAuth, ETag caching, delta uploads, secret scanning (1256 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: No Python equivalent. Critical feature for team collaboration."),
        ("src\\services\\tools\\toolExecution.ts", "services/tools", "Core tool execution engine: permission resolution, pre/post hooks, Zod validation, telemetry, streaming (1463 lines)", "api_server/services/tools_service.py", "analyzed",
         "HIGH: Python is stub-like (~100 lines). Missing: hook system, permission resolution, streaming, telemetry spans."),
        ("src\\services\\compact\\compact.ts", "services/compact", "Full compaction with prompt cache break detection, forked agent pattern, token-based thresholds (1400+ lines)", "api_server/services/compact/compact.py", "analyzed",
         "HIGH: Python compact.py is trivial (134 lines). Missing: token thresholds, AI summarization via forked agent, cache sharing."),
        ("src\\services\\plugins\\PluginInstallationManager.ts", "services/plugins", "Background marketplace reconciliation with progress callbacks (184 lines)", "NONE", "analyzed",
         "HIGH: No Python equivalent for background reconcileMarketplaces, marketplace diffing."),
        ("src\\services\\remoteManagedSettings\\index.ts", "services/settings", "Remote settings management (5 files)", "NONE", "analyzed",
         "HIGH NO_MATCH: SecurityCheck.tsx, syncCache with state machine - no Python equivalent."),
        ("src\\services\\mcp\\auth.ts", "services/mcp", "OAuth 2.0 flow: XAA, PKCE, step-up auth, token caching/revocation (1400+ lines)", "api_server/services/mcp/auth.py", "analyzed",
         "MEDIUM: Python has skeleton but incomplete. Missing XAA flow, step-up detection, RFC 8693."),
        ("src\\services\\mcp\\client.ts", "services/mcp", "MCP client: SSE/HTTP/WS/WebSocket transports, session expiry, auth (1300+ lines)", "api_server/services/mcp/client.py", "analyzed",
         "MEDIUM: Python has 1600+ lines but missing SseIdeTransport, WsIdeTransport, claudeai proxy."),
        ("src\\services\\SessionMemory\\sessionMemory.ts", "services/memory", "Automatic session notes via forked subagent with thresholds (495 lines)", "api_server/services/session_memory.py", "analyzed",
         "MEDIUM: Python has session_memory.py in compact/ but not the SessionMemory service with forked agent pattern."),
        ("src\\services\\extractMemories\\extractMemories.ts", "services/memory", "Extract durable memories via forked agent with TEAMMEM feature (615 lines)", "api_server/services/extract_memories.py", "analyzed",
         "MEDIUM: Python has 416-line implementation with MemoryExtractor but different architecture."),
        ("src\\services\\lsp\\LSPClient.ts", "services/lsp", "JSON-RPC LSP client with crash handling, pending handlers (452 lines)", "api_server/services/lsp/client.py", "analyzed",
         "MEDIUM: Python has 295 lines basic implementation. Missing crash callbacks, pending handler queue."),
        ("src\\services\\AgentSummary\\agentSummary.ts", "services/agent", "Periodic background summarization for coordinator agents (179 lines)", "api_server/services/agent_summary/summary.py", "analyzed",
         "MEDIUM: Python has 132 lines service skeleton. Missing periodic timer summarization."),
        ("src\\services\\autoDream\\autoDream.ts", "services/memory", "Background memory consolidation with time/session gates, lock (329 lines)", "api_server/services/auto_dream/auto_dream.py", "analyzed",
         "MEDIUM: Python has 288 lines but different architecture with post-sampling hook."),
        ("src\\services\\analytics\\index.ts", "services/analytics", "Analytics with Datadog, GrowthBook, event export (179 lines)", "api_server/services/analytics.py", "analyzed",
         "LOW: Python is 148-line stub. Missing Datadog, GrowthBook, sink system, sampling."),
        ("src\\services\\tools\\toolHooks.ts", "services/tools", "Tool pre/post execution hooks system", "NONE", "analyzed",
         "HIGH NO_MATCH: No Python equivalent for hook system."),
        ("src\\services\\tools\\toolOrchestration.ts", "services/tools", "Tool execution orchestration with permission queue", "NONE", "analyzed",
         "HIGH NO_MATCH: No Python equivalent."),
        ("src\\services\\oauth\\auth-code-listener.ts", "services/oauth", "OAuth authorization code listener", "NONE", "analyzed",
         "MEDIUM NO_MATCH: Python has OAuth flow but different implementation."),
        ("src\\services\\oauth\\crypto.ts", "services/oauth", "OAuth cryptographic utilities", "NONE", "analyzed",
         "MEDIUM NO_MATCH: Python has basic crypto."),
        ("src\\services\\MagicDocs\\magicDocs.ts", "services/docs", "Magic Docs integration", "NONE", "analyzed",
         "LOW NO_MATCH: Magic Docs feature not implemented."),
        ("src\\services\\PromptSuggestion\\promptSuggestion.ts", "services/suggestions", "Prompt suggestion with speculation", "NONE", "analyzed",
         "LOW NO_MATCH: Not implemented."),
        ("src\\services\\tips\\tipRegistry.ts", "services/tips", "Tip registry system", "NONE", "analyzed",
         "LOW NO_MATCH: Tips feature not implemented."),
        ("src\\services\\settingsSync\\index.ts", "services/settings", "Settings synchronization", "NONE", "analyzed",
         "LOW NO_MATCH: Settings sync not implemented."),
        ("src\\services\\voice.ts", "services/voice", "Voice streaming/STT integration", "NONE", "analyzed",
         "LOW: Voice service not implemented in Python."),
        ("src\\services\\awaySummary.ts", "services/summary", "Away mode summary generation", "NONE", "analyzed",
         "LOW: Away summary not implemented."),
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
