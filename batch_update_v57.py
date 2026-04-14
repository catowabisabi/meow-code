"""第五十七輪分析批量更新腳本"""
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
        ("src\\utils\\model\\antModels.ts", "utils/model", "ANT models utility", "NONE", "MEDIUM: ANT models."),
        ("src\\utils\\model\\contextWindowUpgradeCheck.ts", "utils/model", "Context window upgrade check", "NONE", "MEDIUM: Context window."),
        ("src\\utils\\model\\modelStrings.ts", "utils/model", "Model strings", "NONE", "MEDIUM: Model strings."),
        ("src\\utils\\model\\modelSupportOverrides.ts", "utils/model", "Model support overrides", "NONE", "MEDIUM: Overrides."),
        ("src\\utils\\model\\validateModel.ts", "utils/model", "Validate model", "NONE", "MEDIUM: Validation."),
        ("src\\utils\\nativeInstaller\\download.ts", "utils/installer", "Native installer download", "NONE", "MEDIUM: Download."),
        ("src\\utils\\nativeInstaller\\index.ts", "utils/installer", "Native installer index", "NONE", "MEDIUM: Index."),
        ("src\\utils\\nativeInstaller\\installer.ts", "utils/installer", "Native installer", "NONE", "MEDIUM: Installer."),
        ("src\\utils\\nativeInstaller\\packageManagers.ts", "utils/installer", "Package managers", "NONE", "MEDIUM: Package managers."),
        ("src\\utils\\nativeInstaller\\pidLock.ts", "utils/installer", "PID lock", "NONE", "MEDIUM: PID lock."),
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