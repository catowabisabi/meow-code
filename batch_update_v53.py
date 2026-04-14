"""第五十三輪分析批量更新腳本"""
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
        ("src\\utils\\claudeInChrome\\setup.ts", "utils/chrome", "Chrome setup", "NONE", "HIGH: Chrome setup."),
        ("src\\utils\\claudeInChrome\\setupPortable.ts", "utils/chrome", "Chrome setup portable", "NONE", "HIGH: Chrome portable."),
        ("src\\utils\\computerUse\\appNames.ts", "utils/computer", "Computer use app names", "NONE", "MEDIUM: App names."),
        ("src\\utils\\computerUse\\cleanup.ts", "utils/computer", "Computer use cleanup", "NONE", "MEDIUM: Cleanup."),
        ("src\\utils\\computerUse\\common.ts", "utils/computer", "Computer use common", "NONE", "MEDIUM: Common."),
        ("src\\utils\\computerUse\\computerUseLock.ts", "utils/computer", "Computer use lock", "NONE", "MEDIUM: Lock."),
        ("src\\utils\\computerUse\\drainRunLoop.ts", "utils/computer", "Computer use drain run loop", "NONE", "MEDIUM: Run loop."),
        ("src\\utils\\computerUse\\escHotkey.ts", "utils/computer", "Computer use ESC hotkey", "NONE", "MEDIUM: Hotkey."),
        ("src\\utils\\computerUse\\executor.ts", "utils/computer", "Computer use executor", "NONE", "HIGH: Executor."),
        ("src\\utils\\computerUse\\gates.ts", "utils/computer", "Computer use gates", "NONE", "MEDIUM: Gates."),
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