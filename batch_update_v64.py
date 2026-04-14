"""第六十四輪分析批量更新腳本"""
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
        ("src\\utils\\bash\\specs\\sleep.ts", "utils/bash", "Bash sleep spec", "NONE", "LOW: Sleep spec."),
        ("src\\utils\\bash\\specs\\srun.ts", "utils/bash", "Bash srun spec", "NONE", "LOW: Srun spec."),
        ("src\\utils\\bash\\specs\\time.ts", "utils/bash", "Bash time spec", "NONE", "LOW: Time spec."),
        ("src\\utils\\bash\\specs\\timeout.ts", "utils/bash", "Bash timeout spec", "NONE", "LOW: Timeout spec."),
        ("src\\utils\\background\\remote\\preconditions.ts", "utils/background", "Background remote preconditions", "NONE", "HIGH: Preconditions."),
        ("src\\utils\\background\\remote\\remoteSession.ts", "utils/background", "Background remote session", "NONE", "HIGH: Remote session."),
        ("src\\tools\\AgentTool\\agentColorManager.ts", "tools/agent", "Agent color manager", "NONE", "MEDIUM: Color manager."),
        ("src\\tools\\AgentTool\\agentDisplay.ts", "tools/agent", "Agent display", "NONE", "MEDIUM: Agent display."),
        ("src\\tools\\AgentTool\\agentMemory.ts", "tools/agent", "Agent memory", "NONE", "HIGH: Agent memory."),
        ("src\\tools\\AgentTool\\agentMemorySnapshot.ts", "tools/agent", "Agent memory snapshot", "NONE", "HIGH: Memory snapshot."),
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