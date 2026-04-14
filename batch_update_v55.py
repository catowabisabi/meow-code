"""第五十五輪分析批量更新腳本"""
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
        ("src\\utils\\hooks\\AsyncHookRegistry.ts", "utils/hooks", "Async hook registry", "NONE", "HIGH: Hook registry."),
        ("src\\utils\\hooks\\execAgentHook.ts", "utils/hooks", "Exec agent hook", "NONE", "HIGH: Agent hook."),
        ("src\\utils\\hooks\\execHttpHook.ts", "utils/hooks", "Exec HTTP hook", "NONE", "HIGH: HTTP hook."),
        ("src\\utils\\hooks\\execPromptHook.ts", "utils/hooks", "Exec prompt hook", "NONE", "HIGH: Prompt hook."),
        ("src\\utils\\hooks\\fileChangedWatcher.ts", "utils/hooks", "File changed watcher", "NONE", "MEDIUM: File watcher."),
        ("src\\utils\\hooks\\hookEvents.ts", "utils/hooks", "Hook events", "NONE", "HIGH: Hook events."),
        ("src\\utils\\hooks\\hookHelpers.ts", "utils/hooks", "Hook helpers", "NONE", "HIGH: Hook helpers."),
        ("src\\utils\\hooks\\hooksConfigSnapshot.ts", "utils/hooks", "Hooks config snapshot", "NONE", "MEDIUM: Config snapshot."),
        ("src\\utils\\hooks\\hooksSettings.ts", "utils/hooks", "Hooks settings", "NONE", "MEDIUM: Hook settings."),
        ("src\\utils\\hooks\\postSamplingHooks.ts", "utils/hooks", "Post sampling hooks", "NONE", "HIGH: Sampling hooks."),
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