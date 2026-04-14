"""第六十二輪分析批量更新腳本"""
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
        ("src\\utils\\teleport\\environments.ts", "utils/teleport", "Teleport environments", "NONE", "HIGH: Environments."),
        ("src\\utils\\teleport\\environmentSelection.ts", "utils/teleport", "Environment selection", "NONE", "HIGH: Env selection."),
        ("src\\utils\\teleport\\gitBundle.ts", "utils/teleport", "Teleport git bundle", "NONE", "HIGH: Git bundle."),
        ("src\\utils\\todo\\types.ts", "utils/todo", "Todo types", "NONE", "LOW: Todo types."),
        ("src\\utils\\ultraplan\\ccrSession.ts", "utils/ultraplan", "UltraPlan CCR session", "NONE", "HIGH: CCR session."),
        ("src\\utils\\ultraplan\\keyword.ts", "utils/ultraplan", "UltraPlan keyword", "NONE", "MEDIUM: Keyword."),
        ("src\\utils\\swarm\\backends\\detection.ts", "utils/swarm", "Swarm backend detection", "NONE", "HIGH: Backend detection."),
        ("src\\utils\\swarm\\backends\\InProcessBackend.ts", "utils/swarm", "In-process backend", "NONE", "HIGH: In-process backend."),
        ("src\\utils\\swarm\\backends\\it2Setup.ts", "utils/swarm", "iTerm2 setup", "NONE", "HIGH: iTerm2 setup."),
        ("src\\utils\\swarm\\backends\\ITermBackend.ts", "utils/swarm", "iTerm backend", "NONE", "HIGH: iTerm backend."),
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