"""第五十四輪分析批量更新腳本"""
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
        ("src\\utils\\computerUse\\hostAdapter.ts", "utils/computer", "Computer use host adapter", "NONE", "HIGH: Host adapter."),
        ("src\\utils\\computerUse\\inputLoader.ts", "utils/computer", "Computer use input loader", "NONE", "MEDIUM: Input loader."),
        ("src\\utils\\computerUse\\mcpServer.ts", "utils/computer", "Computer use MCP server", "NONE", "HIGH: MCP server."),
        ("src\\utils\\computerUse\\setup.ts", "utils/computer", "Computer use setup", "NONE", "HIGH: Setup."),
        ("src\\utils\\computerUse\\swiftLoader.ts", "utils/computer", "Computer use swift loader", "NONE", "MEDIUM: Swift loader."),
        ("src\\utils\\dxt\\helpers.ts", "utils/dxt", "DXT helpers", "NONE", "LOW: DXT helpers."),
        ("src\\utils\\dxt\\zip.ts", "utils/dxt", "DXT zip", "NONE", "LOW: DXT zip."),
        ("src\\utils\\filePersistence\\filePersistence.ts", "utils/persistence", "File persistence", "NONE", "MEDIUM: Persistence."),
        ("src\\utils\\filePersistence\\outputsScanner.ts", "utils/persistence", "Outputs scanner", "NONE", "MEDIUM: Scanner."),
        ("src\\utils\\hooks\\apiQueryHookHelper.ts", "utils/hooks", "API query hook helper", "NONE", "HIGH: Hook helper."),
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