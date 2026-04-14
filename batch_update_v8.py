"""第八輪分析批量更新腳本
更新 bootstrap/main, git, env/shell, llm, webfetch, tree-sitter, config/settings, analytics 模組"""
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
        # Bootstrap/Main Entry Points
        ("src\\main.tsx", "bootstrap/main", "Main entry point (4681 lines): CLI bootstrap, MDM/keychain prefetch, profiling", "main.py (126 lines)", "analyzed",
         "MAJOR: TypeScript has comprehensive CLI bootstrap, Python is simple FastAPI app"),
        ("src\\entrypoints\\cli.tsx", "bootstrap/cli", "CLI fast-path flags (308 lines): --version, --print, --daemon-worker, deep links", "MISSING", "analyzed",
         "CRITICAL: All CLI flags MISSING - Python has no CLI runner"),
        ("src\\entrypoints\\init.ts", "bootstrap/init", "Initialization (345 lines): telemetry/GrowthBook/OAuth/remote settings", "MISSING", "analyzed",
         "MAJOR: Initialization orchestration MISSING"),
        ("src\\bootstrap\\state.ts", "bootstrap/state", "Global state (1600+ lines): ~100 fields for session/cost/token tracking", "MISSING", "analyzed",
         "CRITICAL: Global state management MISSING - Python has no equivalent"),
        ("src\\cli\\print.ts", "cli/headless", "Headless/print mode (5598 lines): query execution loop, hooks, auto-compact", "MISSING", "analyzed",
         "CRITICAL: Headless mode MISSING - 5598 lines of core logic"),
        ("src\\cli\\print.ts", "cli/headless", "Feature flags DCE (100+ flags): COORDINATOR/KAIROS/SSH_REMOTE/BRIDGE_MODE", "MISSING", "analyzed",
         "CRITICAL: Feature flag infrastructure MISSING"),

        # Git Module
        ("src\\utils\\git.ts", "git/core", "Core git utilities (930 lines): findGitRoot, resolveCanonicalRoot, worktree detection", "services/git_service.py (partial)", "analyzed",
         "CRITICAL: resolveCanonicalRoot/security validation MISSING - path traversal risk"),
        ("src\\utils\\gitDiff.ts", "git/diff", "Diff engine (536 lines): structured diffs, hunk parsing, transient state detection", "MISSING", "analyzed",
         "MAJOR: Structured diffs/hunk parsing MISSING"),
        ("src\\utils\\worktree.ts", "git/worktree", "Worktree lifecycle (1525 lines): session tracking, tmux, agent worktrees, sparse checkout", "tools/worktree_tools.py (partial)", "analyzed",
         "MAJOR: Session tracking/sparse checkout MISSING"),
        ("src\\utils\\git\\gitFilesystem.ts", "git/fs-walker", "FS-based git state (705 lines): GitFileWatcher, ref resolution, SHA validation", "MISSING", "analyzed",
         "CRITICAL: GitFileWatcher/caching MISSING - subprocess spam risk"),

        # Env/Shell Module
        ("src\\utils\\env.ts", "env/detection", "Env detection (1000+ lines): 40+ terminals, 30+ clouds, WSL/Docker/SSH", "MISSING", "analyzed",
         "CRITICAL: Terminal detection completely MISSING"),
        ("src\\utils\\subprocessEnv.ts", "env/secrets", "GHA secret scrubbing (20+ secrets stripped from subprocess env)", "MISSING", "analyzed",
         "CRITICAL SECURITY: Python passes ALL env vars to subprocess - secret leak risk"),
        ("src\\utils\\sessionEnvironment.ts", "env/session", "Session env hooks: setup/sessionstart/cwdchanged/filechanged events", "MISSING", "analyzed",
         "MAJOR: Session-scoped env MISSING"),
        ("src\\utils\\shell\\bashProvider.ts", "shell/snapshot", "Shell snapshot (captures ~/.bashrc once, sources for every command)", "MISSING", "analyzed",
         "CRITICAL: Python spawns fresh bash each time - no RC file sourcing"),
        ("src\\utils\\Shell.ts", "shell/cwd", "CWD tracking via pwd>PWD file (persists cd across commands)", "MISSING", "analyzed",
         "CRITICAL: Python has no CWD tracking - cd in command has no effect"),
        ("src\\utils\\shell\\readOnlyCommandValidation.ts", "shell/security", "Read-only command validation (1400 lines): 45+ commands with safe flags", "tools/shell_permissions.py (simple)", "analyzed",
         "MAJOR: Python has simple denylist only - no safe flag maps"),
        ("src\\utils\\shell\\prefix.ts", "shell/llm-prefix", "LLM-backed command prefix extraction (Haiku)", "MISSING", "analyzed",
         "NOTE: CLI-specific for permissions"),

        # LLM Module
        ("src\\services\\api\\client.ts", "llm/multi-provider", "Multi-provider client: firstParty/Bedrock/Vertex/Foundry", "MISSING", "analyzed",
         "CRITICAL: Bedrock/Vertex/Foundry MISSING - only basic adapters"),
        ("src\\services\\api\\claude.ts", "llm/claude-api", "Claude API (1500+ lines): beta headers, retry, token tracking, prompt caching", "adapters/anthropic.py (partial)", "analyzed",
         "MAJOR: Beta headers/retry/token tracking MISSING"),
        ("src\\services\\api\\withRetry.ts", "llm/retry", "Retry with exponential backoff (529 handling, streaming fallback)", "MISSING", "analyzed",
         "MAJOR: Retry logic MISSING in Python adapters"),
        ("src\\query.ts", "llm/query-engine", "Query engine (1300+ lines): streaming, budget tracking, structured output", "ws/chat.py (simplified)", "analyzed",
         "MAJOR: Python ws/chat is simpler, no structured output"),

        # Webfetch Module
        ("src\\tools\\WebFetchTool\\utils.ts", "webfetch/core", "LRU cache (15min/50MB), domain blocklist, AI content processing", "tools/web_fetch.py (basic)", "analyzed",
         "CRITICAL: Cache/domain blocking/AI processing MISSING"),
        ("src\\tools\\WebFetchTool\\preapproved.ts", "webfetch/domains", "Preapproved domains (135+)", "tools/web_fetch.py (6 domains)", "analyzed",
         "CRITICAL: Only 6 domains vs 135+"),
        ("src\\tools\\WebFetchTool\\utils.ts", "webfetch/security", "Secure redirects (same-host only, egress proxy detection)", "MISSING", "analyzed",
         "CRITICAL: Python auto-follows all redirects - security gap"),
        ("src\\utils\\http.ts", "http/utils", "User agent, OAuth 401 retry", "MISSING", "analyzed",
         "MAJOR: OAuth retry MISSING in webfetch"),

        # Tree-sitter/Bash Parser
        ("src\\utils\\bash\\parser.ts", "parser/tree-sitter", "tree-sitter WASM Bash parser: parseCommand, findCommandNode, extractEnvVars", "MISSING", "analyzed",
         "CRITICAL: tree-sitter MISSING - Python has regex only"),
        ("src\\utils\\bash\\ast.ts", "parser/security", "AST security walker: for/while/if extraction, variable tracking", "MISSING", "analyzed",
         "CRITICAL: No AST-based command extraction - regex fallback"),

        # Config/Settings Module
        ("src\\utils\\settings\\settings.ts", "config/multi-source", "Multi-source cascade (user/project/local/flag/policy priority merge)", "db/settings_db.py (flat)", "analyzed",
         "CRITICAL: No source priority/merge - flat key-value only"),
        ("src\\utils\\settings\\mdm\\settings.ts", "config/mdm", "MDM support: macOS plist, Windows Registry, Linux json", "MISSING", "analyzed",
         "CRITICAL: Enterprise MDM MISSING"),
        ("src\\utils\\settings\\types.ts", "config/schema", "Complete Zod schema (1152 lines): 80+ settings fields with validation", "routes/settings.py (6 fields)", "analyzed",
         "CRITICAL: Only 6/80+ fields implemented"),
        ("src\\utils\\settings\\changeDetector.ts", "config/watcher", "File watcher + MDM polling (30min)", "MISSING", "analyzed",
         "MAJOR: Change detection MISSING"),
        ("src\\utils\\settings\\permissionValidation.ts", "config/permission", "Permission rule validation", "MISSING", "analyzed",
         "MAJOR: Permission rule validation MISSING"),

        # Analytics/Telemetry Module
        ("src\\services\\analytics\\index.ts", "analytics/queue", "Event queue with sink attachment", "services/analytics/__init__.py (stub)", "analyzed",
         "CRITICAL: Python __init__.py is empty pass-through"),
        ("src\\services\\analytics\\metadata.ts", "analytics/metadata", "Full metadata enrichment (975 lines): MCP tools, process metrics, GitHub Actions", "services/analytics/metadata.py (partial)", "analyzed",
         "MAJOR: Python missing MCP tool sanitization, CPU% delta, agent identification"),
        ("src\\services\\analytics\\firstPartyEventLogger.ts", "analytics/otel", "OpenTelemetry LoggerProvider + BatchLogRecordProcessor", "MISSING", "analyzed",
         "CRITICAL: Python uses threading.Timer, not OTEL"),
        ("src\\services\\analytics\\growthbook.ts", "analytics/growthbook", "GrowthBook feature flags (1160 lines): periodic refresh, config override", "services/analytics/growthbook.py (partial)", "analyzed",
         "MAJOR: setupPeriodicGrowthBookRefresh/config override MISSING"),
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
