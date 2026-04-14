"""第十八輪分析批量更新腳本
更新 tools, src/root, remaining modules"""
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
        # Tools - databaseTool (HIGH gap - exists but NOT registered)
        ("webui\\tools\\databaseTool.ts", "tools/database", "SQLite tool: create/query/execute/export_csv/drop_table (220 lines)", "api_server/tools/database_tool.py", "analyzed",
         "HIGH: Python database_tool.py EXISTS (340 lines) but NOT registered in register.py - database tool unavailable."),
        
        # src/ root files (CRITICAL/HIGH)
        ("src\\query.ts", "query/core", "Core query engine: streaming, tool execution, auto-compaction, context collapse, reactive compact, budget tracking (1733 lines)", "api_server/agents/tool/loop.py, api_server/services/api/claude.py", "analyzed",
         "CRITICAL: Python loop.py much simpler. Missing: streaming tool execution, reactive compact, media recovery."),
        ("src\\QueryEngine.ts", "query/engine", "Session lifecycle, message handling, SDK compatibility, transcript recording (1299 lines)", "api_server/agents/tool/run_agent.py, api_server/agents/loop.py", "analyzed",
         "CRITICAL: TypeScript QueryEngine is central coordinator for headless/SDK mode. Python equivalents fragmented."),
        ("src\\commands.ts", "commands", "CLI command registration/dispatch for 100+ commands (655 lines)", "api_server/routes/commands.py", "analyzed",
         "HIGH: Python has command routes but lacks sophisticated feature-gated command system."),
        ("src\\context.ts", "context", "System prompt injection, CLAUDE.md auto-discovery, git status (193 lines)", "api_server/prompts/builder.py", "analyzed",
         "MEDIUM: Python lacks CLAUDE.md auto-discovery mechanism."),
        ("src\\cost-tracker.ts", "cost", "API usage tracking, USD cost calculation, cost reporting (327 lines)", "api_server/services/api/usage.py", "analyzed",
         "HIGH: Python has usage tracking but TypeScript has more sophisticated cost calculation with model-specific pricing."),
        ("src\\history.ts", "history", "Conversation history, paste content, history search (468 lines)", "api_server/routes/history.py", "analyzed",
         "HIGH: TypeScript has sophisticated paste store with hash references. Python less comprehensive."),
        ("src\\setup.ts", "setup", "Application initialization: worktree, hooks, terminal backup (480 lines)", "api_server/routes/bootstrap.py", "analyzed",
         "HIGH: TypeScript has comprehensive setup with tmux integration. Python basic."),
        ("src\\Task.ts", "tasks", "Task types: local_bash/local_agent/remote_agent/in_process_teammate (115 lines)", "api_server/agents/task/types.py", "analyzed",
         "MEDIUM: Python has task types but TypeScript has more comprehensive state tracking."),
        ("src\\tools.ts", "tools", "Aggregates 30+ built-in tools (393 lines)", "api_server/tools/*.py", "analyzed",
         "MEDIUM: TypeScript has more sophisticated tool filtering and feature-gated tools."),
        ("src\\costHook.ts", "ui/cost", "React hook for cost display (26 lines)", "NONE", "analyzed",
         "LOW: React-specific frontend component."),
        ("src\\ink.ts", "ui", "React-Ink terminal UI wrapper (89 lines)", "NONE", "analyzed",
         "LOW: React-Ink frontend framework."),
        ("src\\projectOnboardingState.ts", "onboarding", "Project onboarding step management (87 lines)", "NONE", "analyzed",
         "MEDIUM: No Python equivalent for project onboarding state machine."),
        
        # assistant sessionHistory (already tracked - just noting)
        ("src\\assistant\\sessionHistory.ts", "assistant/history", "Remote API session history with pagination (158 lines)", "api_server/services/history/__init__.py", "analyzed",
         "Already tracked - remote API vs local SQLite approach differs."),
        
        # types/generated (protobuf - excluded from types/ but present)
        ("src\\types\\generated\\events_mono\\claude_code\\v1\\claude_code_internal_event.ts", "types/protobuf", "Internal telemetry events via protobuf (870 lines)", "NONE", "analyzed",
         "LOW: Generated protobuf types - infrastructure."),
        ("src\\types\\generated\\events_mono\\common\\v1\\auth.ts", "types/protobuf", "PublicApiAuth protobuf types (105 lines)", "NONE", "analyzed",
         "LOW: Generated protobuf types."),
        ("src\\types\\generated\\events_mono\\growthbook\\v1\\growthbook_experiment_event.ts", "types/protobuf", "GrowthBook experiment events (228 lines)", "NONE", "analyzed",
         "LOW: Generated protobuf types."),
        ("src\\types\\generated\\google\\protobuf\\timestamp.ts", "types/protobuf", "Standard protobuf Timestamp (192 lines)", "NONE", "analyzed",
         "LOW: Generated protobuf types."),
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
