"""第六十六輪分析批量更新腳本"""
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
        ("src\\tools\\BashTool\\sedEditParser.ts", "tools/bash", "SED edit parser", "NONE", "MEDIUM: SED parser."),
        ("src\\tools\\BashTool\\sedValidation.ts", "tools/bash", "SED validation", "NONE", "MEDIUM: SED validation."),
        ("src\\tools\\BashTool\\toolName.ts", "tools/bash", "Bash tool name", "NONE", "LOW: Tool name."),
        ("src\\tools\\BashTool\\utils.ts", "tools/bash", "Bash tool utils", "NONE", "MEDIUM: Bash utils."),
        ("src\\tools\\BriefTool\\attachments.ts", "tools/brief", "Brief tool attachments", "NONE", "MEDIUM: Attachments."),
        ("src\\tools\\BriefTool\\BriefTool.ts", "tools/brief", "Brief tool", "NONE", "MEDIUM: Brief tool."),
        ("src\\tools\\BriefTool\\prompt.ts", "tools/brief", "Brief tool prompt", "NONE", "MEDIUM: Brief prompt."),
        ("src\\tools\\BriefTool\\upload.ts", "tools/brief", "Brief tool upload", "NONE", "MEDIUM: Upload."),
        ("src\\tools\\ConfigTool\\ConfigTool.ts", "tools/config", "Config tool", "NONE", "MEDIUM: Config tool."),
        ("src\\tools\\ConfigTool\\constants.ts", "tools/config", "Config tool constants", "NONE", "LOW: Constants."),
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