"""第五十六輪分析批量更新腳本"""
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
        ("src\\utils\\hooks\\registerFrontmatterHooks.ts", "utils/hooks", "Register frontmatter hooks", "NONE", "HIGH: Frontmatter hooks."),
        ("src\\utils\\hooks\\registerSkillHooks.ts", "utils/hooks", "Register skill hooks", "NONE", "HIGH: Skill hooks."),
        ("src\\utils\\hooks\\skillImprovement.ts", "utils/hooks", "Skill improvement hook", "NONE", "HIGH: Skill improvement."),
        ("src\\utils\\hooks\\ssrfGuard.ts", "utils/hooks", "SSRF guard hook", "NONE", "HIGH: SSRF guard."),
        ("src\\utils\\mcp\\dateTimeParser.ts", "utils/mcp", "MCP datetime parser", "NONE", "MEDIUM: Datetime parser."),
        ("src\\utils\\mcp\\elicitationValidation.ts", "utils/mcp", "MCP elicitation validation", "NONE", "HIGH: Elicitation."),
        ("src\\utils\\memory\\types.ts", "utils/memory", "Memory types", "NONE", "MEDIUM: Memory types."),
        ("src\\utils\\memory\\versions.ts", "utils/memory", "Memory versions", "NONE", "MEDIUM: Memory versions."),
        ("src\\utils\\messages\\mappers.ts", "utils/messages", "Message mappers", "NONE", "MEDIUM: Mappers."),
        ("src\\utils\\messages\\systemInit.ts", "utils/messages", "System init message", "NONE", "MEDIUM: System init."),
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