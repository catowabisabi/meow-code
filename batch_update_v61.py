"""第六十一輪分析批量更新腳本"""
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
        ("src\\utils\\suggestions\\directoryCompletion.ts", "utils/suggestions", "Directory completion", "NONE", "MEDIUM: Directory completion."),
        ("src\\utils\\suggestions\\shellHistoryCompletion.ts", "utils/suggestions", "Shell history completion", "NONE", "MEDIUM: History completion."),
        ("src\\utils\\suggestions\\skillUsageTracking.ts", "utils/suggestions", "Skill usage tracking", "NONE", "MEDIUM: Usage tracking."),
        ("src\\utils\\suggestions\\slackChannelSuggestions.ts", "utils/suggestions", "Slack channel suggestions", "NONE", "MEDIUM: Slack suggestions."),
        ("src\\utils\\task\\diskOutput.ts", "utils/task", "Task disk output", "NONE", "MEDIUM: Disk output."),
        ("src\\utils\\task\\framework.ts", "utils/task", "Task framework", "NONE", "MEDIUM: Framework."),
        ("src\\utils\\task\\outputFormatting.ts", "utils/task", "Task output formatting", "NONE", "MEDIUM: Output formatting."),
        ("src\\utils\\task\\sdkProgress.ts", "utils/task", "Task SDK progress", "NONE", "MEDIUM: SDK progress."),
        ("src\\utils\\task\\TaskOutput.ts", "utils/task", "Task output", "NONE", "MEDIUM: Task output."),
        ("src\\utils\\teleport\\api.ts", "utils/teleport", "Teleport API", "NONE", "HIGH: Teleport API."),
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