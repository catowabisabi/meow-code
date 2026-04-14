"""第十六輪分析批量更新腳本
更新 entrypoints, api/services 模組"""
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
        # Entrypoints (CRITICAL/HIGH)
        ("src\\entrypoints\\sdk\\controlSchemas.ts", "entrypoints/sdk", "SDK control protocol Zod schemas: initialize/interrupt/permission/MCP status/context usage (661 lines)", "NONE", "analyzed",
         "CRITICAL NO_MATCH: No Python equivalent. Python API server lacks SDK control protocol types - core protocol for SDK consumers."),
        ("src\\entrypoints\\sdk\\coreSchemas.ts", "entrypoints/sdk", "Core Zod schemas: ModelUsage/Permission/Hooks (30+ events)/AgentDefinition/SlashCommand (1887 lines)", "api_server/agents/tool/types.py", "analyzed",
         "HIGH: Python has basic ToolDef but lacks comprehensive Zod-style schema validation, 30+ hook events, streaming types."),
        ("src\\entrypoints\\init.ts", "entrypoints/init", "CLI initialization: telemetry/OAuth/policy limits/remote settings/upstream proxy/scratchpad/LSP (345 lines)", "NONE", "analyzed",
         "CRITICAL: Python lifespan only registers tools. Missing: telemetry, OAuth, policy limits, remote settings, upstream proxy."),
        ("src\\entrypoints\\agentSdkTypes.ts", "entrypoints/sdk", "Agent SDK: session management (list/get/rename/fork/tag), CronTask, RemoteControlHandle (443 lines)", "api_server/routes/sessions.py", "analyzed",
         "CRITICAL: Python has basic session routes but missing forkSession/tagSession/renameSession, CronTask, RemoteControlHandle."),
        ("src\\entrypoints\\cli.tsx", "entrypoints/cli", "CLI bootstrap with 15+ fast-path routes (--version/daemon/remote-control/tmux/templates) (308 lines)", "api_server/main.py", "analyzed",
         "HIGH: Python FastAPI lacks CLI routing logic, feature flags, startup profiler, daemon/worker architecture."),
        ("src\\entrypoints\\mcp.ts", "entrypoints/mcp", "MCP server using @modelcontextprotocol/sdk, stdio transport (201 lines)", "api_server/agents/tool/mcp.py", "analyzed",
         "HIGH: Python mcp.py only stubs - actual MCP server implementation missing."),
        ("src\\entrypoints\\sandboxTypes.ts", "entrypoints/sandbox", "Sandbox config schemas: network/filesystem settings with Zod validation (155 lines)", "api_server/sandbox/config.py", "analyzed",
         "HIGH: Python sandbox uses dict-based config, not Zod-typed schemas."),
        ("src\\entrypoints\\sdk\\coreTypes.ts", "entrypoints/sdk", "Re-exports SDK types + HOOK_EVENTS/EXIT_REASONS const arrays (60 lines)", "api_server/agents/tool/types.py", "analyzed",
         "MEDIUM: Python lacks hook event const arrays matching TS."),

        # API Services (src/services/api/ -> api_server/services/api/)
        ("src\\services\\api\\claude.ts", "api/core", "Main Claude API: streaming/message handling/beta headers/tool schemas (3216 lines)", "api_server/services/api/claude.py", "analyzed",
         "HIGH: Python has 1477 lines (55% incomplete). Missing: streaming event handling, beta header management, cache control, fingerprint."),
        ("src\\services\\api\\promptCacheBreakDetection.ts", "api/caching", "Prompt cache break detection via state hashing (682 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No Python equivalent - critical for prompt caching feature."),
        ("src\\services\\api\\errorUtils.ts", "api/errors", "SSL/TLS error detection, HTML sanitization (240 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: SSL error detection critical for enterprise deployments."),
        ("src\\services\\api\\errors.ts", "api/errors", "API error classification, prompt-too-long parsing, nested errors (1118 lines)", "api_server/services/api/errors.py", "analyzed",
         "MEDIUM: Python has 799 lines (28% incomplete). Missing: error type classification, SSL-specific handling."),
        ("src\\services\\api\\logging.ts", "api/telemetry", "API request logging, gateway fingerprinting, usage tracking (753 lines)", "api_server/services/api/logging.py", "analyzed",
         "MEDIUM: Python has 276 lines (63% incomplete). Missing: gateway detection, analytics integration."),
        ("src\\services\\api\\withRetry.ts", "api/resilience", "Retry logic with exponential backoff, fallback triggering (750 lines)", "api_server/services/api/with_retry.py", "analyzed",
         "LOW: Port appears mostly complete."),
        ("src\\services\\api\\filesApi.ts", "api/files", "Anthropic Files API: download/upload with retry (657 lines)", "api_server/services/api/files_api.py", "analyzed",
         "MEDIUM: Python has 91 lines (86% incomplete). Missing: upload functionality, diff generation."),
        ("src\\services\\api\\sessionIngress.ts", "api/persistence", "Session log persistence with conflict resolution (470 lines)", "api_server/services/api/session_ingress.py", "analyzed",
         "LOW: Port appears mostly complete."),
        ("src\\services\\api\\client.ts", "api/auth", "Multi-provider client: Anthropic/Bedrock/Vertex/Foundry (364 lines)", "api_server/services/api/client.py", "analyzed",
         "MEDIUM: Python has 172 lines (37% incomplete). Missing: Azure Foundry support, custom headers."),
        ("src\\services\\api\\grove.ts", "api/notifications", "Grove notification service for policy updates (338 lines)", "api_server/services/api/grove.py", "analyzed",
         "MEDIUM: Python has stubs only - placeholder implementation."),
        ("src\\services\\api\\referral.ts", "api/billing", "Referral/guest pass eligibility (245 lines)", "api_server/services/api/referral.py", "analyzed",
         "MEDIUM: Python has stubs only - minimal logic."),
        ("src\\services\\api\\overageCreditGrant.ts", "api/billing", "Overage credit grant eligibility (132 lines)", "api_server/services/api/overage_credit.py", "analyzed",
         "MEDIUM: Partial implementation - credit formatting missing."),
        ("src\\services\\api\\bootstrap.ts", "api/bootstrap", "Initial config/bootstrap data fetching (133 lines)", "api_server/services/api/bootstrap.py", "analyzed",
         "LOW: Port appears mostly complete."),
        ("src\\services\\api\\dumpPrompts.ts", "api/debug", "Prompt dumping utility for debugging (204 lines)", "api_server/services/api/dump_prompts.py", "analyzed",
         "LOW: Port appears complete."),
        ("src\\services\\api\\metricsOptOut.ts", "api/privacy", "Metrics opt-out preference handling (144 lines)", "api_server/services/api/metrics_opt_out.py", "analyzed",
         "LOW: Port appears complete."),
        ("src\\services\\api\\adminRequests.ts", "api/admin", "Admin request creation/eligibility (102 lines)", "api_server/services/api/admin_requests.py", "analyzed",
         "LOW: Port appears mostly complete."),
        ("src\\services\\api\\firstTokenDate.ts", "api/analytics", "First token timestamp tracking (56 lines)", "api_server/services/api/first_token_date.py", "analyzed",
         "LOW: Port appears complete."),
        ("src\\services\\api\\usage.ts", "api/analytics", "Usage tracking (57 lines)", "api_server/services/api/usage.py", "analyzed",
         "LOW: Port appears complete."),
        ("src\\services\\api\\ultrareviewQuota.ts", "api/review", "UltraReview quota checking (40 lines)", "api_server/services/api/ultra_review_quota.py", "analyzed",
         "MEDIUM: Python stub implementation only."),
        ("src\\services\\api\\emptyUsage.ts", "api/constants", "Empty usage constant (25 lines)", "api_server/services/api/empty_usage.py", "analyzed",
         "LOW: Complete."),
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
