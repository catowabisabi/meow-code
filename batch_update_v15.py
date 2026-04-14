"""第十五輪分析批量更新腳本
更新 models, sessions, coordinator, buddy 模組"""
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
        # Models - Tool (CRITICAL)
        ("src\\Tool.ts", "models/tool", "Full Tool interface: 40+ properties, validateInput, checkPermissions, renderToolUseMessage, maxResultSizeChars (796 lines)", "api_server/models/tool.py", "analyzed",
         "CRITICAL: Python ToolDefinition only has name/description/input_schema. Missing: validateInput, checkPermissions, renderToolUseMessage, maxResultSizeChars, shouldDefer, mcpInfo, isDestructive."),

        # Models - Model utils (HIGH)
        ("src\\utils\\model\\model.ts", "models/llm", "Core model selection: getMainLoopModel, parseUserSpecifiedModel, resolve aliases (sonnet→claude-sonnet-4-6), [1m] suffix, subscription defaults (624 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python has no model selection/parsing logic. No alias resolution, [1m] handling, or subscription-based defaults."),
        ("src\\utils\\model\\modelOptions.ts", "models/llm", "UI model picker options by tier (ant/Max/Pro/PAYG), upgrade hints (544 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No dynamic model option generation by subscription type."),
        ("src\\utils\\model\\configs.ts", "models/llm", "ALL_MODEL_CONFIGS: provider-specific IDs (firstParty/bedrock/vertex/foundry), 12 model configs (122 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python config.py lacks per-provider model ID mappings."),
        ("src\\utils\\model\\modelCapabilities.ts", "models/llm", "Fetches model capabilities (max_tokens) from API, caches to disk with Zod validation (122 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: No Python capability introspection."),
        ("src\\utils\\model\\modelCost.ts", "models/pricing", "Pricing tiers: COST_TIER_3_15/15_75/5_25/30_150, calculateUSDCost() (236 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python has no cost calculation."),
        ("src\\utils\\model\\bedrock.ts", "models/aws", "AWS Bedrock: getInferenceProfileBackingModel, getBedrockRegionPrefix, ARN extraction (269 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python has no Bedrock support."),
        ("src\\utils\\model\\providers.ts", "models/providers", "APIProvider type: firstParty | bedrock | vertex | foundry, isFirstPartyAnthropicBaseUrl (44 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python cannot route to correct API endpoint."),
        ("src\\utils\\model\\agent.ts", "models/agent", "Subagent model inheritance, Bedrock region prefix propagation, aliasMatchesParentTier (161 lines)", "NONE", "analyzed",
         "MEDIUM NO_MATCH: Python lacks subagent tier matching."),
        ("src\\utils\\model\\aliases.ts", "models/aliases", "MODEL_ALIASES: sonnet, opus, haiku, best, sonnet[1m], opus[1m], opusplan (29 lines)", "NONE", "analyzed",
         "MEDIUM: Python has no alias resolution."),
        ("src\\utils\\model\\deprecation.ts", "models/deprecation", "Deprecated models with retirement dates by provider (106 lines)", "NONE", "analyzed",
         "MEDIUM: Python has no deprecation tracking."),
        ("src\\utils\\model\\check1mAccess.ts", "models/context", "checkOpus1mAccess, checkSonnet1mAccess based on cachedExtraUsageDisabledReason (76 lines)", "NONE", "analyzed",
         "MEDIUM: Python has no 1M context access tracking."),
        ("src\\utils\\model\\modelAllowlist.ts", "models/restriction", "isModelAllowed() validates against availableModels, family wildcards (174 lines)", "NONE", "analyzed",
         "MEDIUM: Python has no allowlist enforcement."),
        ("src\\entrypoints\\agentSdkTypes.ts", "models/sdk", "SDK session types: SDKSession, CronTask, RemoteControlHandle (443 lines)", "NONE", "analyzed",
         "HIGH: Python has no SDK session management, cron scheduling, remote control handles."),

        # Coordinator (HIGH)
        ("src\\coordinator\\coordinatorMode.ts", "coordinator", "Coordinator Mode: main agent coordinates workers, distributes tasks, synthesizes results (422 lines)", "api_server/agents/tool/spawn.py", "analyzed",
         "HIGH: Python has basic agent spawning but lacks: isCoordinatorMode, workerToolsContext generation, coordinator system prompt, INTERNAL_WORKER_TOOLS filtering."),

        # Buddy/Companion (HIGH - UI architectural)
        ("src\\buddy\\companion.ts", "companion", "Companion generation: Mulberry32 PRNG seeded by userId, rarity/species/stats (137 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python has no companion generation system."),
        ("src\\buddy\\CompanionSprite.tsx", "companion/ui", "React sprite renderer: speech bubble, pet animation, idle fidget, blinking (377 lines)", "NONE", "analyzed",
         "HIGH: Python API has no terminal UI rendering - architectural gap."),
        ("src\\buddy\\sprites.ts", "companion/assets", "ASCII sprites: 17 species, 3 animation frames, 8 hat types (518 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python has zero ASCII sprite data."),
        ("src\\buddy\\types.ts", "companion/types", "Companion types: RARITIES, SPECIES, EYES, HATS, STAT_NAMES, CompanionBones/Soul (152 lines)", "NONE", "analyzed",
         "MEDIUM: Python lacks all companion type definitions."),
        ("src\\buddy\\prompt.ts", "companion/prompt", "Companion intro text generation (40 lines)", "NONE", "analyzed",
         "LOW: Python lacks companion intro generation."),
        ("src\\buddy\\useBuddyNotification.tsx", "companion/ui", "React hook for buddy notification state, /buddy trigger detection (104 lines)", "NONE", "analyzed",
         "MEDIUM: Python has no hook equivalent."),

        # Sessions (CRITICAL/HIGH)
        ("src\\utils\\sessionStorage.ts", "sessions/storage", "JSONL transcript persistence: 50MB limit, UUID dedup, sidechain for subagents, CCR v2 writer (1500+ lines)", "api_server/services/session_store.py", "analyzed",
         "CRITICAL: Python uses simple JSON files. Missing: buffering, UUID dedup, sidechain, CCR v2 writer, tombstone rewriting."),
        ("src\\utils\\sessionRestore.ts", "sessions/restore", "Full session resume: worktree restoration, agent restoration, context-collapse, attribution snapshots", "NONE", "analyzed",
         "CRITICAL NO_MATCH: Python has no session resume - no worktree/agent attribution restoration."),
        ("src\\utils\\sessionState.ts", "sessions/state", "State machine: idle/running/requires_action with SDK event emission", "NONE", "analyzed",
         "HIGH NO_MATCH: Python has no session state machine."),
        ("src\\bridge\\sessionRunner.ts", "sessions/process", "Subprocess spawner with NDJSON parsing, activity tracking, permission forwarding (560 lines)", "NONE", "analyzed",
         "HIGH: Python spawns async loops, not CLI child processes with stdio pipeline."),
        ("src\\services\\SessionMemory\\sessionMemory.ts", "sessions/memory", "AI memory extraction from session transcripts using Sonnet (495 lines)", "api_server/services/session_memory.py", "analyzed",
         "HIGH: Python uses key-value storage, not AI semantic extraction."),
        ("src\\services\\compact\\sessionMemoryCompact.ts", "sessions/compact", "Memory compaction during session compaction with micro-compact, auto-dream", "api_server/services/compact/session_memory.py", "analyzed",
         "HIGH: Python has stub only."),
        ("src\\bridge\\codeSessionApi.ts", "sessions/api", "CCR v2 HTTP wrappers for /v1/code/sessions/* (168 lines)", "api_server/services/api/session_ingress.py", "analyzed",
         "MEDIUM: Different API (v1 vs CCR v2)."),
        ("src\\remote\\RemoteSessionManager.ts", "sessions/remote", "Remote session lifecycle via WebSocket/SSE (347 lines)", "NONE", "analyzed",
         "HIGH NO_MATCH: Python lacks remote session lifecycle management."),
        ("src\\remote\\SessionsWebSocket.ts", "sessions/remote", "WebSocket transport for session events (408 lines)", "NONE", "analyzed",
         "MEDIUM: Python WebSocket routing exists but different architecture."),
        ("src\\utils\\sessionIngressAuth.ts", "sessions/auth", "Session ingress token refresh", "NONE", "analyzed",
         "MEDIUM: Python ingress token handling different."),
        ("src\\assistant\\sessionHistory.ts", "sessions/history", "Session history hooks for UI", "NONE", "analyzed",
         "MEDIUM: Python has basic FTS5 search."),
        ("src\\utils\\listSessionsImpl.ts", "sessions/list", "Session enumeration with filtering", "api_server/routes/sessions.py", "analyzed",
         "LOW: Functional equivalent exists."),
        ("src\\utils\\sessionTitle.ts", "sessions/title", "Auto-generate session titles from first user message", "api_server/services/session_store.py", "analyzed",
         "LOW: Similar logic exists."),
        ("src\\utils\\concurrentSessions.ts", "sessions/tracking", "Track multiple concurrent sessions per project", "NONE", "analyzed",
         "LOW: Python lacks concurrent tracking."),
        ("src\\types\\logs.ts", "sessions/types", "20+ entry types: progress, attribution-snapshot, content-replacement, marble-origami-*, worktree-state (400+ lines)", "api_server/models/message.py", "analyzed",
         "CRITICAL: Python only has basic Message model."),
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
