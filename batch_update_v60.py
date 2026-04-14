"""第六十輪分析批量更新腳本"""
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
        ("src\\utils\\settings\\validateEditTool.ts", "utils/settings", "Validate edit tool", "NONE", "MEDIUM: Edit tool validation."),
        ("src\\utils\\settings\\validationTips.ts", "utils/settings", "Validation tips", "NONE", "LOW: Validation tips."),
        ("src\\utils\\shell\\outputLimits.ts", "utils/shell", "Shell output limits", "NONE", "MEDIUM: Output limits."),
        ("src\\utils\\shell\\powershellDetection.ts", "utils/shell", "PowerShell detection", "NONE", "MEDIUM: PS detection."),
        ("src\\utils\\shell\\powershellProvider.ts", "utils/shell", "PowerShell provider", "NONE", "MEDIUM: PS provider."),
        ("src\\utils\\shell\\resolveDefaultShell.ts", "utils/shell", "Resolve default shell", "NONE", "MEDIUM: Default shell."),
        ("src\\utils\\shell\\shellProvider.ts", "utils/shell", "Shell provider", "NONE", "MEDIUM: Shell provider."),
        ("src\\utils\\shell\\shellToolUtils.ts", "utils/shell", "Shell tool utils", "NONE", "MEDIUM: Shell utils."),
        ("src\\utils\\shell\\specPrefix.ts", "utils/shell", "Spec prefix", "NONE", "LOW: Spec prefix."),
        ("src\\utils\\skills\\skillChangeDetector.ts", "utils/skills", "Skill change detector", "NONE", "HIGH: Skill detector."),
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