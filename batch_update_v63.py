"""第六十三輪分析批量更新腳本"""
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
        ("src\\utils\\swarm\\backends\\PaneBackendExecutor.ts", "utils/swarm", "Pane backend executor", "NONE", "HIGH: Pane executor."),
        ("src\\utils\\swarm\\backends\\registry.ts", "utils/swarm", "Swarm backend registry", "NONE", "HIGH: Backend registry."),
        ("src\\utils\\swarm\\backends\\teammateModeSnapshot.ts", "utils/swarm", "Teammate mode snapshot", "NONE", "HIGH: Snapshot."),
        ("src\\utils\\swarm\\backends\\types.ts", "utils/swarm", "Swarm backend types", "NONE", "HIGH: Types."),
        ("src\\utils\\settings\\mdm\\constants.ts", "utils/mdm", "MDM constants", "NONE", "MEDIUM: MDM constants."),
        ("src\\utils\\settings\\mdm\\rawRead.ts", "utils/mdm", "MDM raw read", "NONE", "MEDIUM: MDM read."),
        ("src\\utils\\bash\\specs\\alias.ts", "utils/bash", "Bash alias spec", "NONE", "LOW: Alias spec."),
        ("src\\utils\\bash\\specs\\index.ts", "utils/bash", "Bash specs index", "NONE", "LOW: Specs index."),
        ("src\\utils\\bash\\specs\\nohup.ts", "utils/bash", "Bash nohup spec", "NONE", "LOW: Nohup spec."),
        ("src\\utils\\bash\\specs\\pyright.ts", "utils/bash", "Bash pyright spec", "NONE", "LOW: Pyright spec."),
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