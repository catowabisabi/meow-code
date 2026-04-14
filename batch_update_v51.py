"""第五十一輪分析批量更新腳本"""
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
        ("src\\utils\\workloadContext.ts", "utils", "Workload context", "NONE", "MEDIUM: Workload context."),
        ("src\\utils\\worktreeModeEnabled.ts", "utils", "Worktree mode enabled", "NONE", "HIGH: Worktree mode."),
        ("src\\utils\\xdg.ts", "utils", "XDG utility", "NONE", "LOW: XDG."),
        ("src\\utils\\xml.ts", "utils", "XML utility", "NONE", "LOW: XML."),
        ("src\\utils\\yaml.ts", "utils", "YAML utility", "NONE", "LOW: YAML."),
        ("src\\utils\\zodToJsonSchema.ts", "utils", "Zod to JSON schema", "NONE", "LOW: Zod."),
        ("src\\utils\\bash\\bashParser.ts", "utils/bash", "Bash parser", "NONE", "MEDIUM: Bash parser."),
        ("src\\utils\\bash\\bashPipeCommand.ts", "utils/bash", "Bash pipe command", "NONE", "MEDIUM: Bash pipe."),
        ("src\\utils\\bash\\heredoc.ts", "utils/bash", "Heredoc utility", "NONE", "LOW: Heredoc."),
        ("src\\utils\\bash\\ParsedCommand.ts", "utils/bash", "Parsed command", "NONE", "LOW: Parsed command."),
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