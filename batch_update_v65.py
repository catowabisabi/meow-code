"""第六十五輪分析批量更新腳本"""
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
        ("src\\tools\\AgentTool\\constants.ts", "tools/agent", "Agent tool constants", "NONE", "LOW: Constants."),
        ("src\\tools\\AgentTool\\resumeAgent.ts", "tools/agent", "Resume agent", "NONE", "HIGH: Resume agent."),
        ("src\\tools\\AskUserQuestionTool\\prompt.ts", "tools/ask", "Ask user prompt", "NONE", "MEDIUM: User prompt."),
        ("src\\tools\\BashTool\\bashPermissions.ts", "tools/bash", "Bash tool permissions", "NONE", "HIGH: Bash permissions."),
        ("src\\tools\\BashTool\\bashSecurity.ts", "tools/bash", "Bash tool security", "NONE", "HIGH: Bash security."),
        ("src\\tools\\BashTool\\commandSemantics.ts", "tools/bash", "Command semantics", "NONE", "MEDIUM: Semantics."),
        ("src\\tools\\BashTool\\commentLabel.ts", "tools/bash", "Comment label", "NONE", "LOW: Comment label."),
        ("src\\tools\\BashTool\\destructiveCommandWarning.ts", "tools/bash", "Destructive command warning", "NONE", "HIGH: Destructive warning."),
        ("src\\tools\\BashTool\\modeValidation.ts", "tools/bash", "Mode validation", "NONE", "HIGH: Mode validation."),
        ("src\\tools\\BashTool\\prompt.ts", "tools/bash", "Bash tool prompt", "NONE", "MEDIUM: Bash prompt."),
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