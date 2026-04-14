"""第二十一輪分析批量更新腳本
更新 cli/handlers, cli/transports, commands 模組"""
import sqlite3
from datetime import datetime

DB_PATH = r"F:\codebase\cato-claude\progress.db"
TS_SRC = r"F:\codebase\cato-claude\_claude_code_leaked_source_code"

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

def analyze_and_update(src_path, category, summary, api_path, notes):
    rows = update_record(src_path, category, summary, api_path, "analyzed", notes)
    if rows > 0:
        print(f"[+] {src_path}")
    else:
        print(f"[-] Not found: {src_path}")
    return rows

def main():
    updates = [
        # cli/exit.ts
        ("src\\cli\\exit.ts", "cli/shutdown", "CLI exit handler: graceful shutdown, cleanup, exit codes", "NONE", "CRITICAL: No Python graceful shutdown handler."),
        
        # cli/handlers/*
        ("src\\cli\\handlers\\agents.ts", "cli/handlers", "Agent mode handlers", "NONE", "MEDIUM: Agent mode CLI handlers."),
        ("src\\cli\\handlers\\autoMode.ts", "cli/handlers", "Auto mode handlers", "NONE", "MEDIUM: Auto mode CLI handlers."),
        ("src\\cli\\handlers\\mcp.tsx", "cli/handlers", "MCP CLI handlers", "NONE", "MEDIUM: MCP CLI handlers."),
        ("src\\cli\\handlers\\plugins.ts", "cli/handlers", "Plugin CLI handlers", "NONE", "MEDIUM: Plugin CLI handlers."),
        ("src\\cli\\handlers\\util.tsx", "cli/handlers", "Utility CLI handlers", "NONE", "LOW: Utility CLI handlers."),
        
        # cli/ndjsonSafeStringify.ts
        ("src\\cli\\ndjsonSafeStringify.ts", "cli/io", "NDJSON safe stringification", "NONE", "MEDIUM: No NDJSON safe stringifier."),
        
        # cli/remoteIO.ts
        ("src\\cli\\remoteIO.ts", "cli/io", "Remote IO streaming: SSE/JSON-RPC hybrid (10079 lines)", "NONE", "HIGH: No Python remote IO streaming."),
        
        # cli/structuredIO.ts
        ("src\\cli\\structuredIO.ts", "cli/io", "Structured IO: print/println/multiline tools (28870 lines)", "NONE", "HIGH: No Python structured IO."),
        
        # cli/transports/*
        ("src\\cli\\transports\\HybridTransport.ts", "cli/transports", "Hybrid HTTP/SSE transport", "NONE", "CRITICAL: No Python hybrid transport."),
        ("src\\cli\\transports\\SSETransport.ts", "cli/transports", "Server-Sent Events transport", "NONE", "CRITICAL: No Python SSE transport."),
        ("src\\cli\\transports\\SerialBatchEventUploader.ts", "cli/transports", "Serial batch event uploader", "NONE", "HIGH: No batch upload mechanism."),
        ("src\\cli\\transports\\WebSocketTransport.ts", "cli/transports", "WebSocket transport layer", "NONE", "CRITICAL: No Python WebSocket transport."),
        ("src\\cli\\transports\\WorkerStateUploader.ts", "cli/transports", "Web Worker state uploader", "NONE", "HIGH: No worker state mechanism."),
        ("src\\cli\\transports\\ccrClient.ts", "cli/transports", "CCR client transport", "NONE", "HIGH: CCR transport missing."),
        ("src\\cli\\transports\\transportUtils.ts", "cli/transports", "Transport utilities", "NONE", "MEDIUM: Transport utils missing."),
        
        # cli/update.ts
        ("src\\cli\\update.ts", "cli/update", "CLI self-update mechanism (14588 lines)", "NONE", "HIGH: No Python self-update."),
        
        # commands/*
        ("src\\commands\\bridge-kick.ts", "commands/bridge", "Bridge kickoff command", "NONE", "CRITICAL: Bridge kickoff missing."),
        ("src\\commands\\brief.ts", "commands/brief", "Brief mode command", "NONE", "MEDIUM: Brief mode command."),
        ("src\\commands\\commit-push-pr.ts", "commands/git", "Full git: commit + push + PR workflow", "NONE", "HIGH: Full git workflow missing."),
        ("src\\commands\\createMovedToPluginCommand.ts", "commands/migrate", "Command migration to plugin", "NONE", "MEDIUM: Migration helper."),
        ("src\\commands\\cost\\cost.ts", "commands/cost", "Cost tracking display", "NONE", "MEDIUM: Cost display command."),
        ("src\\commands\\doctor\\doctor.tsx", "commands/doctor", "System diagnostics doctor", "NONE", "MEDIUM: Diagnostics command."),
        ("src\\commands\\diff\\diff.tsx", "commands/diff", "Diff visualization", "NONE", "MEDIUM: Diff UI component."),
        ("src\\commands\\context\\context-noninteractive.ts", "commands/context", "Non-interactive context command", "NONE", "MEDIUM: Non-interactive context."),
        ("src\\commands\\context\\context.tsx", "commands/context", "Context management command", "NONE", "MEDIUM: Context management command."),
    ]

    total = 0
    for src_path, category, summary, api_path, notes in updates:
        rows = analyze_and_update(src_path, category, summary, api_path, notes)
        total += rows

    print(f"\nTotal records updated: {total}")

if __name__ == "__main__":
    main()