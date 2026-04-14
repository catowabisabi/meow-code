"""第十九輪分析批量更新腳本
更新 types, services, utils 模組"""
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
        # Types (7 files - HIGH/CRITICAL gaps)
        ("src\\types\\command.ts", "types/commands", "CLI command types: LocalCommand/PromptCommand/LocalJSXCommand discriminated unions (221 lines)", "api_server/routes/commands.py", "analyzed", "MEDIUM: Python has slash command endpoints but lacks discriminated union type system."),
        ("src\\types\\hooks.ts", "types/hooks", "Hook system: HookEvent/HookInput/HookCallback/HookResult with Zod schemas (294 lines)", "api_server/routes/hooks.py", "analyzed", "HIGH: TypeScript has comprehensive Zod-validated hook schemas with 12+ event types. Python lacks Zod validation and type-safe hook routing."),
        ("src\\types\\ids.ts", "types/identity", "Branded types SessionId/AgentId with compile-time safety (48 lines)", "NONE", "analyzed", "HIGH: Python lacks branded types - Session.id is plain str. No compile-time safety for ID mixing."),
        ("src\\types\\logs.ts", "types/logs", "Log types: SerializedMessage/TranscriptMessage/15+ entry types (335 lines)", "api_server/models/session.py", "analyzed", "MEDIUM: Python has Session/Message models but lacks comprehensive log entry discriminated union."),
        ("src\\types\\permissions.ts", "types/permissions", "PermissionMode/Behavior/Rule, YoloClassifierResult with 2-stage XML (441 lines)", "api_server/routes/permissions.py", "analyzed", "HIGH: TypeScript has granular PermissionDecisionReason discriminated union. Python has simple Pydantic models."),
        ("src\\types\\plugin.ts", "types/plugins", "PluginError discriminated union with 25+ variants (368 lines)", "api_server/services/plugins/manager.py", "analyzed", "MEDIUM: Python has plugin loading but lacks PluginError discriminated union."),
        ("src\\types\\textInputTypes.ts", "types/input", "Text input props: VimTextInput/Queue/OrphanedPermission types (392 lines)", "api_server/routes/commands.py", "analyzed", "MEDIUM: Python has queue endpoints but lacks Vim mode tracking, inline ghost text."),

        # Services - pending files with gaps
        ("src\\services\\awaySummary.ts", "services/summary", "AI-powered 'while you were away' session recap (79 lines)", "NONE", "analyzed", "MEDIUM: Python has no AI session recap - needs context extraction + model call."),
        ("src\\services\\claudeAiLimits.ts", "services/billing", "Claude AI rate limits: 5hr/7day/overage with header parsing (520 lines)", "api_server/services/policy_limits/", "analyzed", "HIGH: Python policy_limits lacks TypeScript's sophisticated header-based limit detection."),
        ("src\\services\\diagnosticTracking.ts", "services/lsp", "IDE diagnostic tracking: baseline capture, diff detection (402 lines)", "api_server/services/lsp/diagnostic_tracking.py", "analyzed", "MEDIUM: Python has diagnostic_tracking but TypeScript has richer baseline tracking."),
        ("src\\services\\notifier.ts", "services/notifications", "Cross-platform notifications: iTerm2/Kitty/Ghostty (161 lines)", "api_server/services/notifier.py", "analyzed", "LOW: Python notifier.py likely already implemented."),
        ("src\\services\\rateLimitMessages.ts", "services/billing", "Rate limit message generation with upsell logic (344 lines)", "api_server/services/rate_limit_messages.py", "analyzed", "MEDIUM: Python has rate_limit_messages.py; parity needs verification."),
        ("src\\services\\tokenEstimation.ts", "services/api", "Token counting: API/Bedrock/Haiku fallback, thinking blocks (500 lines)", "api_server/services/token_estimation.py", "analyzed", "HIGH: Python token_estimation lacks Bedrock/Haiku fallbacks."),
        ("src\\services\\voice.ts", "services/voice", "Audio recording: cpal/SoX/arecord fallbacks (530 lines)", "api_server/services/voice.py", "analyzed", "HIGH: Python voice.py parity with TypeScript native audio needs verification."),
        ("src\\services\\voiceKeyterms.ts", "services/voice", "Voice STT keyword boosting: project name, branch, files (111 lines)", "NONE", "analyzed", "MEDIUM: No Python STT keyword optimization equivalent."),
        ("src\\services\\voiceStreamSTT.ts", "services/voice", "WebSocket voice_stream client for push-to-talk STT (549 lines)", "NONE", "analyzed", "HIGH: Python has no voice stream WebSocket client equivalent."),

        # Utils - CRITICAL gaps from analysis
        ("src\\utils\\Shell.ts", "utils/shell", "CWD tracking via pwd>PWD file - cd persists across commands", "NONE", "analyzed", "CRITICAL NO_MATCH: Python has no CWD tracking - cd in command has no effect."),
        ("src\\utils\\auth.ts", "utils/auth", "OAuth/API key/keychain/AWS/GCP refresh (1533+ lines)", "NONE", "analyzed", "CRITICAL NO_MATCH: Full auth system missing - no OAuth, no keychain, no cloud refresh."),
        ("src\\utils\\bash\\parser.ts", "utils/parser", "tree-sitter WASM Bash parser", "NONE", "analyzed", "CRITICAL NO_MATCH: tree-sitter MISSING - Python has regex only."),
        ("src\\utils\\bash\\ast.ts", "utils/parser", "AST security walker: for/while/if extraction", "NONE", "analyzed", "CRITICAL NO_MATCH: No AST-based command extraction - regex fallback only."),
        ("src\\utils\\cronScheduler.ts", "utils/scheduler", "Scheduler with lock, missed task detection, backoff", "NONE", "analyzed", "CRITICAL NO_MATCH: Scheduler lock mechanism missing - thundering herd risk."),
        ("src\\utils\\cronTasksLock.ts", "utils/scheduler", "O_EXCL atomic lock, PID liveness, stale lock recovery", "NONE", "analyzed", "CRITICAL NO_MATCH: Distributed lock missing."),
        ("src\\utils\\env.ts", "utils/env", "40+ terminals, 30+ clouds, WSL/Cygwin detection (1000+ lines)", "NONE", "analyzed", "CRITICAL NO_MATCH: Terminal detection completely missing."),
        ("src\\utils\\git\\gitFilesystem.ts", "git/filesystem", "SHA/ref validation, GitFileWatcher caching, worktree support", "NONE", "analyzed", "CRITICAL NO_MATCH: No Python equivalent - TypeScript reads .git/ directly avoiding subprocess."),
        ("src\\utils\\ide.ts", "utils/ide", "IDE detection: VS Code/Cursor/Windsurf/JetBrains", "NONE", "analyzed", "CRITICAL NO_MATCH: detectIDEs/findAvailableIDE MISSING."),
        ("src\\utils\\model\\model.ts", "models/llm", "Core model selection, alias resolution, [1m] handling", "NONE", "analyzed", "CRITICAL: No Python model selection/parsing logic."),
        ("src\\utils\\model\\providers.ts", "models/providers", "firstParty/bedrock/vertex/foundry routing", "NONE", "analyzed", "CRITICAL: Python cannot route to correct API endpoint."),
        ("src\\utils\\sandbox\\sandbox-adapter.ts", "sandbox/core", "@anthropic-ai/sandbox-runtime wrapper (990 lines)", "api_server/sandbox/sandboxed_shell.py", "analyzed", "CRITICAL: bareGitRepoScrubPaths security feature missing."),
        ("src\\utils\\sessionState.ts", "sessions/state", "idle/running/requires_action state machine", "NONE", "analyzed", "CRITICAL: Python has no session state machine."),
        ("src\\utils\\sessionStorage.ts", "sessions/storage", "JSONL transcript: 50MB limit, UUID dedup, sidechain (1500+ lines)", "api_server/services/session_store.py", "analyzed", "CRITICAL: Python uses simple JSON files - missing buffering, UUID dedup."),
        ("src\\utils\\settings\\types.ts", "config/types", "1152 lines Zod schema: 80+ settings fields", "api_server/routes/settings.py", "analyzed", "CRITICAL: Only 6/80+ fields implemented."),
        ("src\\utils\\swarm\\inProcessRunner.ts", "swarm/execution", "In-process teammate with AsyncLocalStorage isolation (1500+ lines)", "NONE", "analyzed", "CRITICAL NO_MATCH: No Python in-process execution - AsyncLocalStorage has no Python equivalent."),
        ("src\\utils\\swarm\\spawnInProcess.ts", "swarm/spawn", "In-process teammate spawning with TeammateIdentity (333 lines)", "NONE", "analyzed", "CRITICAL NO_MATCH: No in-process spawning with TeammateIdentity."),
        ("src\\utils\\worktree.ts", "git/worktree", "Worktree lifecycle: tmux, hooks, symlinks, sparse-checkout (1525 lines)", "api_server/tools/worktree_tools.py", "analyzed", "CRITICAL: Python has only basic wrappers - missing tmux, hooks, sparse-checkout."),
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
