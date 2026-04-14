"""第二十輪分析批量更新腳本
更新 telemetry, deepLink, permissions, plugins 模組"""
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
        # telemetry (9 files - HIGH/CRITICAL gaps)
        ("src\\utils\\telemetry\\sessionTracing.ts", "telemetry/tracing", "OpenTelemetry spans for interactions/LLM/tools/hooks with AsyncLocalStorage (938 lines)", "NONE", "analyzed", "HIGH: No Python OTEL span tracing for LLM requests, tool execution."),
        ("src\\utils\\telemetry\\betaSessionTracing.ts", "telemetry/tracing", "Beta tracing: system prompt hashing, tool schema tracking (496 lines)", "NONE", "analyzed", "HIGH: No beta tracing features."),
        ("src\\utils\\telemetry\\perfettoTracing.ts", "telemetry/tracing", "Chrome Perfetto DevTools trace format with TTFT/TTLT metrics (1125 lines)", "NONE", "analyzed", "MEDIUM: Perfetto tracing is visualization feature."),
        ("src\\utils\\telemetry\\bigqueryExporter.ts", "telemetry/metrics", "BigQuery metrics exporter with trust dialog check (256 lines)", "NONE", "analyzed", "HIGH: No BigQuery export equivalent."),
        ("src\\utils\\telemetry\\instrumentation.ts", "telemetry/otel", "Full OTEL initialization: OTLPgrpc/OTLP-http/Prometheus exporters (829 lines)", "NONE", "analyzed", "HIGH: No Python OTEL initialization infrastructure."),
        ("src\\utils\\telemetry\\pluginTelemetry.ts", "telemetry/analytics", "Plugin lifecycle analytics with privacy pattern (294 lines)", "NONE", "analyzed", "MEDIUM: No plugin analytics equivalent."),
        ("src\\utils\\telemetry\\skillLoadedEvent.ts", "telemetry/analytics", "Skill loaded event tracking (43 lines)", "NONE", "analyzed", "MEDIUM: No skill loading analytics."),
        ("src\\utils\\telemetry\\events.ts", "telemetry/events", "OTEL event logger with sequence tracking (79 lines)", "api_server/services/analytics/event_exporter.py", "analyzed", "LOW: Partial equivalent exists."),
        ("src\\utils\\telemetry\\logger.ts", "telemetry/logging", "DiagLogger for OTEL diagnostics (30 lines)", "NONE", "analyzed", "LOW: OTEL diag logger not needed in Python."),

        # deepLink (6 files - HIGH gaps)
        ("src\\utils\\deepLink\\terminalLauncher.ts", "deep_link/terminal", "Terminal emulator detection/spawning: Ghostty/Alacritty/Kitty/WezTerm/iTerm (563 lines)", "NONE", "analyzed", "HIGH: No Python equivalent - desktop terminal launching."),
        ("src\\utils\\deepLink\\registerProtocol.ts", "deep_link/protocol", "OS protocol handler registration: macOS .app/Linux .desktop/Windows registry (354 lines)", "NONE", "analyzed", "HIGH: No Python protocol registration equivalent."),
        ("src\\utils\\deepLink\\protocolHandler.ts", "deep_link/handler", "handleDeepLinkUri entry point with cwd resolution (142 lines)", "NONE", "analyzed", "MEDIUM: Desktop URI handling."),
        ("src\\utils\\deepLink\\parseDeepLink.ts", "deep_link/parser", "URI parser with security validation: control char rejection, length caps (176 lines)", "NONE", "analyzed", "LOW: URI parsing could be shared."),
        ("src\\utils\\deepLink\\banner.ts", "deep_link/ui", "Warning banner for deep-link-originated sessions (129 lines)", "NONE", "analyzed", "LOW: UI component."),
        ("src\\utils\\deepLink\\terminalPreference.ts", "deep_link/pref", "TERM_PROGRAM detection and persistent storage (60 lines)", "NONE", "analyzed", "LOW: Terminal preference capture."),

        # permissions (24 files - CRITICAL/HIGH gaps)
        ("src\\utils\\permissions\\shellRuleMatching.ts", "permissions/parsing", "Shell rule matching: exact/prefix/wildcard patterns (234 lines)", "NONE", "analyzed", "CRITICAL: No Python equivalent - core permission rule parsing missing."),
        ("src\\utils\\permissions\\filesystem.ts", "permissions/fs", "File system permission checks: dangerous path detection, NTFS streams, UNC (1445+ lines)", "NONE", "analyzed", "CRITICAL: Entire filesystem permission system missing in Python."),
        ("src\\utils\\permissions\\yoloClassifier.ts", "permissions/classifier", "Auto-mode AI classifier: 2-stage XML classification (1464+ lines)", "NONE", "analyzed", "CRITICAL: No Python YOLO auto-mode classifier equivalent."),
        ("src\\utils\\permissions\\permissions.ts", "permissions/core", "Core permission checking: hasPermissionsToUseTool (1400+ lines)", "NONE", "analyzed", "CRITICAL: Main permission entry point entirely missing."),
        ("src\\utils\\permissions\\permissionSetup.ts", "permissions/setup", "Permission context initialization: dangerous classifier detection (1471+ lines)", "NONE", "analyzed", "CRITICAL: Permission setup entirely missing."),
        ("src\\utils\\permissions\\permissionsLoader.ts", "permissions/persistence", "Permission rule persistence: disk load/save (300 lines)", "NONE", "analyzed", "CRITICAL: Rule persistence entirely missing."),
        ("src\\utils\\permissions\\pathValidation.ts", "permissions/validation", "Path validation: tilde expansion, glob patterns, scratchpad (489 lines)", "NONE", "analyzed", "CRITICAL: Path validation for safety missing."),
        ("src\\utils\\permissions\\PermissionUpdate.ts", "permissions/operations", "Permission update application and persistence (393 lines)", "NONE", "analyzed", "CRITICAL: Update operations missing."),
        ("src\\utils\\permissions\\dangerousPatterns.ts", "permissions/security", "Dangerous patterns: kubectl/aws/gh/curl/npm (85 lines)", "api_server/tools/shell_permissions.py", "analyzed", "HIGH: Python has partial denylist but lacks ANT-specific patterns."),
        ("src\\utils\\permissions\\classifierShared.ts", "permissions/classifier", "Classifier response parsing infrastructure (45 lines)", "NONE", "analyzed", "HIGH: No classifier response parsing in Python."),
        ("src\\utils\\permissions\\PermissionPromptToolResultSchema.ts", "permissions/schema", "Zod schemas for permission prompt input/output (131 lines)", "NONE", "analyzed", "HIGH: No Zod schema for permission prompts."),
        ("src\\utils\\permissions\\PermissionUpdateSchema.ts", "permissions/schema", "Zod schemas for permission updates (75 lines)", "NONE", "analyzed", "HIGH: No update operation schemas."),
        ("src\\utils\\permissions\\denialTracking.ts", "permissions/state", "Denial tracking: DENIAL_LIMITS (maxConsecutive:3, maxTotal:20) (50 lines)", "NONE", "analyzed", "HIGH: No denial tracking state management."),
        ("src\\utils\\permissions\\autoModeState.ts", "permissions/state", "Auto mode state and circuit breaker (43 lines)", "NONE", "analyzed", "HIGH: No auto mode state management."),
        ("src\\utils\\permissions\\bypassPermissionsKillswitch.ts", "permissions/gate", "Statsig gate for bypass permissions (159 lines)", "NONE", "analyzed", "HIGH: No Statsig integration for permissions."),
        ("src\\utils\\permissions\\permissionExplainer.ts", "permissions/explain", "AI-powered permission explanation with risk levels (254 lines)", "NONE", "analyzed", "HIGH: No AI permission explanation."),
        ("src\\utils\\permissions\\permissionRuleParser.ts", "permissions/parsing", "Permission rule string parsing with escape sequences (202 lines)", "NONE", "analyzed", "HIGH: No rule string parser."),
        ("src\\utils\\permissions\\PermissionMode.ts", "permissions/modes", "Permission mode definitions: default/plan/acceptEdits/bypass/auto (145 lines)", "NONE", "analyzed", "MEDIUM: Mode definitions missing."),
        ("src\\utils\\permissions\\getNextPermissionMode.ts", "permissions/modes", "Permission mode cycling (Shift+Tab) (105 lines)", "NONE", "analyzed", "MEDIUM: Mode cycling logic missing."),
        ("src\\utils\\permissions\\PermissionResult.ts", "permissions/types", "Permission result types (39 lines)", "NONE", "analyzed", "MEDIUM: Result type definitions missing."),
        ("src\\utils\\permissions\\PermissionRule.ts", "permissions/types", "Permission rule types (44 lines)", "NONE", "analyzed", "MEDIUM: Rule type definitions missing."),
        ("src\\utils\\permissions\\classifierDecision.ts", "permissions/classifier", "SAFE_YOLO_ALLOWLISTED_TOOLS for read-only skip (102 lines)", "NONE", "analyzed", "MEDIUM: Tool allowlisting logic missing."),
        ("src\\utils\\permissions\\shadowedRuleDetection.ts", "permissions/analysis", "Shadowed rule detection with fix suggestions (238 lines)", "NONE", "analyzed", "MEDIUM: Rule shadowing analysis missing."),
        ("src\\utils\\permissions\\bashClassifier.ts", "permissions/classifier", "Bash classifier stub - ANT-only (65 lines)", "NONE", "analyzed", "LOW: ANT-only stub."),

        # plugins (44 files - CRITICAL/HIGH gaps)
        ("src\\utils\\plugins\\pluginLoader.ts", "plugins/loader", "Core plugin loading: git clone/npm install/manifest validation (2000+ lines)", "api_server/services/plugins/installer.py", "analyzed", "CRITICAL: Python has stubs only - git/npm/validation all missing."),
        ("src\\utils\\plugins\\marketplaceManager.ts", "plugins/marketplace", "Full marketplace management: GCS/GitHub/reconciliation (2643 lines)", "NONE", "analyzed", "CRITICAL: No marketplace management equivalent."),
        ("src\\utils\\plugins\\installedPluginsManager.ts", "plugins/state", "Plugin installation state with V1/V2 migration (1268 lines)", "api_server/services/plugins/operations.py", "analyzed", "HIGH: V1/V2 migration missing."),
        ("src\\utils\\plugins\\dependencyResolver.ts", "plugins/dependencies", "apt-style transitive dependency resolution (311 lines)", "NONE", "analyzed", "CRITICAL: No dependency resolution equivalent."),
        ("src\\utils\\plugins\\loadPluginCommands.ts", "plugins/commands", "Slash command loading with SKILL.md support (950 lines)", "NONE", "analyzed", "HIGH: No slash command loading."),
        ("src\\utils\\plugins\\loadPluginAgents.ts", "plugins/agents", "Agent loading from plugin directories (352 lines)", "NONE", "analyzed", "HIGH: No agent loading from plugins."),
        ("src\\utils\\plugins\\loadPluginHooks.ts", "plugins/hooks", "26+ hook event types with Zod validation (291 lines)", "NONE", "analyzed", "CRITICAL: No hook system equivalent."),
        ("src\\utils\\plugins\\loadPluginOutputStyles.ts", "plugins/styles", "Output style loading (182 lines)", "NONE", "analyzed", "MEDIUM: No output style loading."),
        ("src\\utils\\plugins\\lspPluginIntegration.ts", "plugins/lsp", "LSP server config from .lsp.json (391 lines)", "NONE", "analyzed", "HIGH: No LSP plugin integration."),
        ("src\\utils\\plugins\\marketplaceHelpers.ts", "plugins/marketplace", "Policy enforcement, blocklist, formatting (596 lines)", "NONE", "analyzed", "HIGH: No policy enforcement."),
        ("src\\utils\\plugins\\pluginOptionsStorage.ts", "plugins/config", "Secure plugin options with keychain (400 lines)", "api_server/services/plugins/config.py", "analyzed", "HIGH: secureStorage (keychain) missing."),
        ("src\\utils\\plugins\\pluginDirectories.ts", "plugins/dirs", "Plugin directory paths, seed dirs (178 lines)", "api_server/services/plugins/config.py", "analyzed", "MEDIUM: Seed dirs, data dirs missing."),
        ("src\\utils\\plugins\\cacheUtils.ts", "plugins/cache", "Cache lifecycle: orphan cleanup, GC (200 lines)", "NONE", "analyzed", "HIGH: No cache lifecycle management."),
        ("src\\utils\\plugins\\installCounts.ts", "plugins/marketplace", "GitHub install counts (292 lines)", "NONE", "analyzed", "MEDIUM: No install counts equivalent."),
        ("src\\utils\\plugins\\fetchTelemetry.ts", "plugins/telemetry", "Network fetch telemetry (135 lines)", "NONE", "analyzed", "MEDIUM: No telemetry equivalent."),
        ("src\\utils\\plugins\\gitAvailability.ts", "plugins/git", "Git availability detection (69 lines)", "NONE", "analyzed", "MEDIUM: No git detection."),
        ("src\\utils\\plugins\\headlessPluginInstall.ts", "plugins/install", "Headless/CCR plugin installation (174 lines)", "NONE", "analyzed", "HIGH: No headless installation."),
        ("src\\utils\\plugins\\hintRecommendation.ts", "plugins/recommend", "Plugin hint recommendations (164 lines)", "NONE", "analyzed", "LOW: No hint recommendation."),
        ("src\\utils\\plugins\\addDirPluginSettings.ts", "plugins/settings", "--add-dir plugin settings (77 lines)", "NONE", "analyzed", "MEDIUM: No --add-dir equivalent."),
        ("src\\utils\\plugins\\pluginAutoupdate.ts", "plugins/update", "Plugin auto-update logic", "NONE", "analyzed", "HIGH: No autoupdate equivalent."),
        ("src\\utils\\plugins\\pluginBlocklist.ts", "plugins/policy", "Enterprise blocklist", "NONE", "analyzed", "HIGH: No blocklist equivalent."),
        ("src\\utils\\plugins\\pluginIdentifier.ts", "plugins/id", "Plugin ID parsing", "NONE", "analyzed", "LOW: Basic ID parsing."),
        ("src\\utils\\plugins\\pluginInstallationHelpers.ts", "plugins/install", "Installation helper functions", "NONE", "analyzed", "HIGH: No installation helpers."),
        ("src\\utils\\plugins\\pluginPolicy.ts", "plugins/policy", "Enterprise policy enforcement", "NONE", "analyzed", "HIGH: No policy equivalent."),
        ("src\\utils\\plugins\\pluginStartupCheck.ts", "plugins/startup", "Plugin startup validation", "NONE", "analyzed", "MEDIUM: No startup checks."),
        ("src\\utils\\plugins\\pluginVersioning.ts", "plugins/version", "Version calculation from git SHA", "NONE", "analyzed", "MEDIUM: No version calculation."),
        ("src\\utils\\plugins\\reconciler.ts", "plugins/reconcile", "Marketplace reconciliation", "NONE", "analyzed", "HIGH: No reconciliation."),
        ("src\\utils\\plugins\\refresh.ts", "plugins/refresh", "Plugin refresh logic", "NONE", "analyzed", "MEDIUM: No refresh equivalent."),
        ("src\\utils\\plugins\\schemas.ts", "plugins/schemas", "Zod schemas for plugin types", "NONE", "analyzed", "MEDIUM: No Zod schemas."),
        ("src\\utils\\plugins\\validatePlugin.ts", "plugins/validate", "Plugin validation", "NONE", "analyzed", "MEDIUM: No validation."),
        ("src\\utils\\plugins\\walkPluginMarkdown.ts", "plugins/walk", "Markdown file walking", "NONE", "analyzed", "LOW: No markdown walker."),
        ("src\\utils\\plugins\\zipCache.ts", "plugins/cache", "ZIP cache mode for containers", "NONE", "analyzed", "HIGH: No ZIP cache."),
        ("src\\utils\\plugins\\zipCacheAdapters.ts", "plugins/cache", "ZIP cache filesystem adapters", "NONE", "analyzed", "HIGH: No ZIP cache adapters."),
        ("src\\utils\\plugins\\lspRecommendation.ts", "plugins/recommend", "LSP plugin recommendation", "NONE", "analyzed", "LOW: No LSP recommendation."),
        ("src\\utils\\plugins\\managedPlugins.ts", "plugins/managed", "Managed plugin handling", "NONE", "analyzed", "MEDIUM: No managed plugin concept."),
        ("src\\utils\\plugins\\mcpPluginIntegration.ts", "plugins/mcp", "MCP server integration", "api_server/services/mcp/", "analyzed", "MEDIUM: Partial - plugin integration missing."),
        ("src\\utils\\plugins\\mcpbHandler.ts", "plugins/mcp", "MCPB user config handling", "NONE", "analyzed", "LOW: No MCPB equivalent."),
        ("src\\utils\\plugins\\officialMarketplace.ts", "plugins/marketplace", "Official Claude marketplace", "NONE", "analyzed", "HIGH: No official marketplace."),
        ("src\\utils\\plugins\\officialMarketplaceGcs.ts", "plugins/marketplace", "GCS bucket marketplace source", "NONE", "analyzed", "HIGH: No GCS source."),
        ("src\\utils\\plugins\\officialMarketplaceStartupCheck.ts", "plugins/startup", "Startup marketplace validation", "NONE", "analyzed", "MEDIUM: No startup checks."),
        ("src\\utils\\plugins\\orphanedPluginFilter.ts", "plugins/filter", "Orphaned plugin filtering", "NONE", "analyzed", "LOW: No orphan filtering."),
        ("src\\utils\\plugins\\parseMarketplaceInput.ts", "plugins/marketplace", "Marketplace input parsing", "NONE", "analyzed", "MEDIUM: No input parsing."),
        ("src\\utils\\plugins\\performStartupChecks.tsx", "plugins/startup", "Startup plugin checks", "NONE", "analyzed", "MEDIUM: No startup checks."),
        ("src\\utils\\plugins\\pluginFlagging.ts", "plugins/flag", "Plugin flagging for errors", "NONE", "analyzed", "LOW: No flagging system."),
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
