"""第十四輪分析批量更新腳本
更新 types, constants, utils, core/main 模組"""
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
        # Main entry point
        ("src\\main.tsx", "core/cli", "CLI entry with commander.js: 50+ flags (--debug/--print/--model/--agent/etc.), MDM/keychain prefetch, client type detection, deep link handling, SSH/Kairos modes (4680 lines)", "NONE", "analyzed",
         "HIGH: No Python CLI equivalent. Python api_server is FastAPI HTTP server only. MDM/keychain prefetch has no Python equivalent."),

        # Utils (HIGH priority)
        ("src\\utils\\git.ts", "utils/git", "Git operations: findGitRoot, worktree resolution, stash, diff, preserveGitStateForIssue, remote URL normalization (930 lines)", "api_server/services/git_service.py", "analyzed",
         "HIGH: Python git_service.py (265 lines) lacks: worktree detection, canonical root resolution, preserveGitStateForIssue, remote hash normalization."),
        ("src\\utils\\path.ts", "utils/path", "expandPath (~, relative, POSIX on Windows), toRelativePath, containsPathTraversal, normalizePathForConfigKey (159 lines)", "api_server/tools/path_validation.py", "analyzed",
         "HIGH: Python path_validation is PowerShell-specific (480 lines). Lacks generic expandPath, cross-platform normalization."),
        ("src\\utils\\errors.ts", "utils/errors", "Custom error classes (ClaudeError/AbortError/ShellError), isAbortError, classifyAxiosError, shortErrorStack (242 lines)", "api_server/services/api/errors.py", "analyzed",
         "HIGH: Python errors.py focuses on API error classification. Lacks custom error hierarchy, FsInaccessible helpers."),
        ("src\\utils\\log.ts", "utils/logging", "Error logging, session logs, in-memory error cache, error sinks, log loading/parsing (369 lines)", "api_server/services/internal_logging.py", "analyzed",
         "MEDIUM: Python logging (147 lines) lacks error sink abstraction, log file loading/parsing."),
        ("src\\utils\\file.ts", "utils/filesystem", "File read/write, pathExists, encoding detection, atomic write, symlink handling (588 lines)", "api_server/tools/file_tools.py", "analyzed",
         "MEDIUM: Python file_tools.py simpler; lacks atomic write pattern, symlink preservation."),
        ("src\\utils\\debug.ts", "utils/debug", "Debug logging with file output, filtering, latest log symlink (272 lines)", "NONE", "analyzed",
         "MEDIUM: API server uses standard Python logging instead."),
        ("src\\utils\\github\\ghAuthStatus.ts", "utils/github", "Detects gh CLI installation and authentication state (33 lines)", "NONE", "analyzed",
         "MEDIUM: CLI-specific feature not needed in API server."),
        ("src\\utils\\formatBriefTimestamp.ts", "utils/timestamp", "Format ISO timestamps for display (87 lines)", "NONE", "analyzed",
         "LOW: Python has built-in datetime formatting."),
        ("src\\utils\\uuid.ts", "utils/uuid", "UUID validation, createAgentId (31 lines)", "NONE", "analyzed",
         "LOW: Python uses built-in uuid module."),
        ("src\\utils\\hash.ts", "utils/hash", "djb2Hash, hashContent, hashPair (52 lines)", "NONE", "analyzed",
         "LOW: Python uses hashlib instead."),
        ("src\\utils\\bufferedWriter.ts", "utils/io", "Buffered async file writer with flush interval (104 lines)", "NONE", "analyzed",
         "LOW: Python asyncio handles this natively."),

        # Types (CRITICAL/HIGH)
        ("src\\types\\hooks.ts", "types/hooks", "HookCallback/HookResult types, Zod schemas for hook JSON validation (300+ lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: No Python equivalent of SDK hook types, prompt elicitation protocol, hook event types."),
        ("src\\types\\permissions.ts", "types/permissions", "PermissionMode, PermissionRule, YoloClassifierResult, ClassifierUsage (400+ lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python has bash_security.py but no YoloClassifier, classifier stages, usage tracking."),
        ("src\\types\\command.ts", "types/command", "LocalCommand, PromptCommand, LocalJSXCommand with availability/context (200+ lines)", "NONE", "analyzed",
         "HIGH: Python has route handlers but no equivalent command type system."),
        ("src\\types\\logs.ts", "types/logs", "LogOption, TranscriptMessage, AttributionSnapshot, ContentReplacement types (400+ lines)", "NONE", "analyzed",
         "HIGH: Python has basic Session/Messages but no attribution snapshots, content replacement."),
        ("src\\types\\plugin.ts", "types/plugin", "PluginManifest, LoadedPlugin, 20+ error variants in PluginError union (400+ lines)", "NONE", "analyzed",
         "HIGH: Python has plugin manager but no PluginManifest schema or error discriminated union."),
        ("src\\types\\ids.ts", "types/ids", "SessionId, AgentId branded string types (100+ lines)", "NONE", "analyzed",
         "MEDIUM: Python Session uses plain strings. Brand types pattern not implemented."),
        ("src\\types\\textInputTypes.ts", "types/input", "TextInputProps, VimTextInput, QueuedCommand, QueuePriority (400+ lines)", "NONE", "analyzed",
         "LOW: UI types irrelevant for API server."),

        # Constants (HIGH/CRITICAL)
        ("src\\constants\\prompts.ts", "constants/prompts", "getSystemPrompt: session guidance, output efficiency, tone/style sections (1400+ lines)", "api_server/prompts/builder.py", "analyzed",
         "CRITICAL: Python builder.py lacks session guidance, output efficiency, tone/style sections."),
        ("src\\constants\\oauth.ts", "constants/oauth", "OAuth config: 13+ URLs, scope arrays for claude.ai/console (300+ lines)", "NONE", "analyzed",
         "HIGH: Python oauth_service.py lacks OAuth URL/scopes constants."),
        ("src\\constants\\outputStyles.ts", "constants/styles", "OutputStyleConfig, Explanatory/Learning mode prompts (400+ lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Explanatory/Learning modes not implemented in Python."),
        ("src\\constants\\system.ts", "constants/system", "getCLISyspromptPrefix, getAttributionHeader with cc_version/cc_entrypoint (150+ lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python has no attribution header generation with fingerprinting."),
        ("src\\constants\\systemPromptSections.ts", "constants/prompts", "systemPromptSection caching, cacheBreak semantics (100+ lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python has no prompt section caching system."),
        ("src\\constants\\tools.ts", "constants/tools", "ALL_AGENT_DISALLOWED_TOOLS, ASYNC_AGENT_ALLOWED_TOOLS sets (126 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python has no agent mode tool permission sets."),
        ("src\\constants\\apiLimits.ts", "constants/api", "API_IMAGE_MAX_BASE64_SIZE (5MB), PDF limits (20MB/100pages), media limits (100/request)", "NONE", "analyzed",
         "MEDIUM: Python has no centralized API limit constants."),
        ("src\\constants\\betas.ts", "constants/betas", "Beta header strings: HEAD, interleaved-thinking, context-1m, tool-search, effort, task-budgets (80+ lines)", "NONE", "analyzed",
         "MEDIUM: Python passes beta headers via adapter but no centralized tracking."),
        ("src\\constants\\files.ts", "constants/files", "BINARY_EXTENSIONS (100+ extensions), hasBinaryExtension (150+ lines)", "NONE", "analyzed",
         "MEDIUM: Python file_tools.py has no binary extension list."),
        ("src\\constants\\product.ts", "constants/product", "PRODUCT_URL, CLAUDE_AI_BASE_URL, getRemoteSessionUrl (100+ lines)", "NONE", "analyzed",
         "MEDIUM: Python routes lack session URL helpers."),
        ("src\\constants\\toolLimits.ts", "constants/tools", "DEFAULT_MAX_RESULT_SIZE_CHARS (50K), MAX_TOOL_RESULT_TOKENS (100K) (100+ lines)", "NONE", "analyzed",
         "MEDIUM: Python ToolDef has no max_result_size concept."),
        ("src\\constants\\github-app.ts", "constants/github", "PR_TITLE, WORKFLOW_CONTENT, PR_BODY for GitHub App integration (200+ lines)", "NONE", "analyzed",
         "LOW: GitHub App feature not relevant to API server."),
        ("src\\constants\\errorIds.ts", "constants/errors", "E_TOOL_USE_SUMMARY_GENERATION_FAILED = 344 (50+ lines)", "NONE", "analyzed",
         "LOW: Python has exception classes but no numeric error ID tracking."),
        ("src\\constants\\common.ts", "constants/common", "getLocalISODate, getSessionStartDate, getLocalMonthYear (50+ lines)", "NONE", "analyzed",
         "LOW: Python datetime handling varies but no functional gap."),
        ("src\\constants\\keys.ts", "constants/config", "getGrowthBookClientKey() for ant/external builds (30+ lines)", "NONE", "analyzed",
         "LOW: Python has GrowthBook but different integration."),
        ("src\\constants\\messages.ts", "constants/messages", "NO_CONTENT_MESSAGE constant (20+ lines)", "NONE", "analyzed",
         "LOW: Minor constant."),
        ("src\\constants\\spinnerVerbs.ts", "constants/ui", "SPINNER_VERBS array (~150 past-tense verbs) (200+ lines)", "NONE", "analyzed",
         "LOW: UI feature not relevant to API server."),
        ("src\\constants\\turnCompletionVerbs.ts", "constants/ui", "TURN_COMPLETION_VERBS array (~8 verbs) (17 lines)", "NONE", "analyzed",
         "LOW: UI feature."),
        ("src\\constants\\xml.ts", "constants/xml", "XML tag constants for command/bash/task/teammate/fork messages (91 lines)", "NONE", "analyzed",
         "MEDIUM: Python message parsing may use different tag conventions."),
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
