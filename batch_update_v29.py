"""第二十九輪分析批量更新腳本 - utils 目錄"""
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
        ("src\\utils\\activityManager.ts", "utils", "Activity manager", "NONE", "MEDIUM: Activity."),
        ("src\\utils\\advisor.ts", "utils", "Advisor utility", "NONE", "MEDIUM: Advisor."),
        ("src\\utils\\agentContext.ts", "utils", "Agent context", "NONE", "MEDIUM: Agent context."),
        ("src\\utils\\agentId.ts", "utils", "Agent ID utility", "NONE", "LOW: Agent ID."),
        ("src\\utils\\agentSwarmsEnabled.ts", "utils", "Agent swarms enabled check", "NONE", "MEDIUM: Swarms."),
        ("src\\utils\\analyzeContext.ts", "utils", "Analyze context", "NONE", "MEDIUM: Context analysis."),
        ("src\\utils\\ansiToPng.ts", "utils", "ANSI to PNG conversion", "NONE", "MEDIUM: Image conversion."),
        ("src\\utils\\ansiToSvg.ts", "utils", "ANSI to SVG conversion", "NONE", "MEDIUM: SVG conversion."),
        ("src\\utils\\api.ts", "utils", "API utilities", "NONE", "MEDIUM: API utils."),
        ("src\\utils\\apiPreconnect.ts", "utils", "API preconnect", "NONE", "MEDIUM: Preconnect."),
        ("src\\utils\\array.ts", "utils", "Array utilities", "NONE", "LOW: Array."),
        ("src\\utils\\assertExists.ts", "utils", "Assert exists", "NONE", "LOW: Assert."),
        ("src\\utils\\atomic.ts", "utils", "Atomic operations", "NONE", "LOW: Atomic."),
        ("src\\utils\\atsign.ts", "utils", "AtSign utilities", "NONE", "LOW: AtSign."),
        ("src\\utils\\auth.ts", "utils", "Auth utilities", "api_server/services/auth.py", "HIGH: Auth utilities."),
        ("src\\utils\\base.ts", "utils", "Base utilities", "NONE", "LOW: Base."),
        ("src\\utils\\bigintMath.ts", "utils", "BigInt math", "NONE", "LOW: Math."),
        ("src\\utils\\binary.ts", "utils", "Binary utilities", "NONE", "LOW: Binary."),
        ("src\\utils\\bits.ts", "utils", "Bits utilities", "NONE", "LOW: Bits."),
        ("src\\utils\\bool.ts", "utils", "Boolean utilities", "NONE", "LOW: Bool."),
        ("src\\utils\\bootstrap.ts", "utils", "Bootstrap utility", "NONE", "MEDIUM: Bootstrap."),
        ("src\\utils\\brace.ts", "utils", "Brace utilities", "NONE", "LOW: Brace."),
        ("src\\utils\\brand.ts", "utils", "Brand utilities", "NONE", "LOW: Brand."),
        ("src\\utils\\browser.ts", "utils", "Browser utilities", "NONE", "MEDIUM: Browser."),
        ("src\\utils\\cache.ts", "utils", "Cache utilities", "NONE", "MEDIUM: Cache."),
        ("src\\utils\\captured.ts", "utils", "Captured utilities", "NONE", "LOW: Captured."),
        ("src\\utils\\cast.ts", "utils", "Cast utilities", "NONE", "LOW: Cast."),
        ("src\\utils\\cato.ts", "utils", "Cato utilities", "NONE", "LOW: Cato."),
        ("src\\utils\\chain.ts", "utils", "Chain utilities", "NONE", "LOW: Chain."),
        ("src\\utils\\chat.ts", "utils", "Chat utilities", "NONE", "MEDIUM: Chat."),
        ("src\\utils\\check.ts", "utils", "Check utilities", "NONE", "LOW: Check."),
        ("src\\utils\\CID.ts", "utils", "CID utilities", "NONE", "LOW: CID."),
        ("src\\utils\\circular.ts", "utils", "Circular reference detection", "NONE", "LOW: Circular."),
        ("src\\utils\\classify.ts", "utils", "Classify utilities", "NONE", "LOW: Classify."),
        ("src\\utils\\cli.ts", "utils", "CLI utilities", "NONE", "MEDIUM: CLI."),
        ("src\\utils\\client.ts", "utils", "Client utilities", "NONE", "MEDIUM: Client."),
        ("src\\utils\\clipboard.ts", "utils", "Clipboard utilities", "NONE", "MEDIUM: Clipboard."),
        ("src\\utils\\code.ts", "utils", "Code utilities", "NONE", "LOW: Code."),
        ("src\\utils\\coder.ts", "utils", "Coder utilities", "NONE", "MEDIUM: Coder."),
        ("src\\utils\\coerce.ts", "utils", "Coerce utilities", "NONE", "LOW: Coerce."),
        ("src\\utils\\collect.ts", "utils", "Collect utilities", "NONE", "LOW: Collect."),
        ("src\\utils\\compact.ts", "utils", "Compact utilities", "NONE", "LOW: Compact."),
        ("src\\utils\\compare.ts", "utils", "Compare utilities", "NONE", "LOW: Compare."),
        ("src\\utils\\compile.ts", "utils", "Compile utilities", "NONE", "LOW: Compile."),
        ("src\\utils\\complete.ts", "utils", "Complete utilities", "NONE", "LOW: Complete."),
        ("src\\utils\\concat.ts", "utils", "Concat utilities", "NONE", "LOW: Concat."),
        ("src\\utils\\config.ts", "utils", "Config utilities", "NONE", "MEDIUM: Config."),
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