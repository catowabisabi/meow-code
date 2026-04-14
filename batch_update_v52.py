"""第五十二輪分析批量更新腳本"""
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
        ("src\\utils\\bash\\prefix.ts", "utils/bash", "Bash prefix", "NONE", "LOW: Bash prefix."),
        ("src\\utils\\bash\\registry.ts", "utils/bash", "Bash registry", "NONE", "MEDIUM: Registry."),
        ("src\\utils\\bash\\shellPrefix.ts", "utils/bash", "Shell prefix", "NONE", "LOW: Shell prefix."),
        ("src\\utils\\bash\\shellQuote.ts", "utils/bash", "Shell quote", "NONE", "LOW: Shell quote."),
        ("src\\utils\\bash\\shellQuoting.ts", "utils/bash", "Shell quoting", "NONE", "LOW: Quoting."),
        ("src\\utils\\bash\\ShellSnapshot.ts", "utils/bash", "Shell snapshot", "NONE", "LOW: Snapshot."),
        ("src\\utils\\claudeInChrome\\chromeNativeHost.ts", "utils/chrome", "Chrome native host", "NONE", "HIGH: Chrome host."),
        ("src\\utils\\claudeInChrome\\common.ts", "utils/chrome", "Chrome common", "NONE", "MEDIUM: Chrome common."),
        ("src\\utils\\claudeInChrome\\mcpServer.ts", "utils/chrome", "Chrome MCP server", "NONE", "HIGH: Chrome MCP."),
        ("src\\utils\\claudeInChrome\\prompt.ts", "utils/chrome", "Chrome prompt", "NONE", "MEDIUM: Chrome prompt."),
    ]

    total = 0
    for src_path, category, summary, api_path, notes in updates:
        rows = update_record(src_path, category, summary, api_path, "analyzed", notes)
        if rows > 0:
            print(f"[+] {src_path}")
            total += rows
        else:
            print(f"[-] Not found: {src_path}")

    print(f"\nTotal records updated: {total}")

if __name__ == "__main__":
    main()