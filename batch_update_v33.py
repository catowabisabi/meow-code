"""第三十三輪分析批量更新腳本"""
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
        ("src\\utils\\collapseTeammateShutdowns.ts", "utils", "Collapse teammate shutdowns", "NONE", "LOW: Teammate."),
        ("src\\utils\\combinedAbortSignal.ts", "utils", "Combined abort signal", "NONE", "LOW: Abort signal."),
        ("src\\utils\\commandLifecycle.ts", "utils", "Command lifecycle", "NONE", "MEDIUM: Command lifecycle."),
        ("src\\utils\\commitAttribution.ts", "utils", "Commit attribution", "NONE", "MEDIUM: Git attribution."),
        ("src\\utils\\completionCache.ts", "utils", "Completion cache", "NONE", "MEDIUM: Cache."),
        ("src\\utils\\configConstants.ts", "utils", "Config constants", "NONE", "LOW: Constants."),
        ("src\\utils\\contentArray.ts", "utils", "Content array", "NONE", "LOW: Content array."),
        ("src\\utils\\contextAnalysis.ts", "utils", "Context analysis", "NONE", "MEDIUM: Context analysis."),
        ("src\\utils\\contextSuggestions.ts", "utils", "Context suggestions", "NONE", "MEDIUM: Suggestions."),
        ("src\\utils\\controlMessageCompat.ts", "utils", "Control message compat", "NONE", "LOW: Compat."),
        ("src\\utils\\convert.ts", "utils", "Convert utility", "NONE", "LOW: Convert."),
        ("src\\utils\\cookie.ts", "utils", "Cookie utility", "NONE", "MEDIUM: Cookie."),
        ("src\\utils\\copy.ts", "utils", "Copy utility", "NONE", "LOW: Copy."),
        ("src\\utils\\core.ts", "utils", "Core utility", "NONE", "LOW: Core."),
        ("src\\utils\\cost.ts", "utils", "Cost utility", "NONE", "MEDIUM: Cost."),
        ("src\\utils\\count.ts", "utils", "Count utility", "NONE", "LOW: Count."),
        ("src\\utils\\counter.ts", "utils", "Counter utility", "NONE", "LOW: Counter."),
        ("src\\utils\\country.ts", "utils", "Country utility", "NONE", "LOW: Country."),
        ("src\\utils\\couple.ts", "utils", "Couple utility", "NONE", "LOW: Couple."),
        ("src\\utils\\coverage.ts", "utils", "Coverage utility", "NONE", "LOW: Coverage."),
        ("src\\utils\\create.ts", "utils", "Create utility", "NONE", "LOW: Create."),
        ("src\\utils\\createRequire.ts", "utils", "Create require", "NONE", "LOW: Require."),
        ("src\\utils\\crossplatform.ts", "utils", "Cross platform utility", "NONE", "LOW: Crossplatform."),
        ("src\\utils\\crypt.ts", "utils", "Crypt utility", "NONE", "LOW: Crypt."),
        ("src\\utils\\cursor.ts", "utils", "Cursor utility", "NONE", "LOW: Cursor."),
        ("src\\utils\\customElement.ts", "utils", "Custom element", "NONE", "LOW: Custom element."),
        ("src\\utils\\customer.ts", "utils", "Customer utility", "NONE", "MEDIUM: Customer."),
        ("src\\utils\\cycle.ts", "utils", "Cycle utility", "NONE", "LOW: Cycle."),
        ("src\\utils\\damerau.ts", "utils", "Damerau levenshtein", "NONE", "LOW: Distance."),
        ("src\\utils\\datasource.ts", "utils", "Datasource utility", "NONE", "MEDIUM: Datasource."),
        ("src\\utils\\datetime.ts", "utils", "Datetime utility", "NONE", "LOW: Datetime."),
        ("src\\utils\\day.ts", "utils", "Day utility", "NONE", "LOW: Day."),
        ("src\\utils\\dbox.ts", "utils", "Dbox utility", "NONE", "LOW: Dbox."),
        ("src\\utils\\debug.ts", "utils", "Debug utility", "NONE", "LOW: Debug."),
        ("src\\utils\\decrypt.ts", "utils", "Decrypt utility", "NONE", "MEDIUM: Decrypt."),
        ("src\\utils\\delay.ts", "utils", "Delay utility", "NONE", "LOW: Delay."),
        ("src\\utils\\delegate.ts", "utils", "Delegate utility", "NONE", "LOW: Delegate."),
        ("src\\utils\\delete.ts", "utils", "Delete utility", "NONE", "LOW: Delete."),
        ("src\\utils\\delimiter.ts", "utils", "Delimiter utility", "NONE", "LOW: Delimiter."),
        ("src\\utils\\dependency.ts", "utils", "Dependency utility", "NONE", "LOW: Dependency."),
        ("src\\utils\\deploy.ts", "utils", "Deploy utility", "NONE", "MEDIUM: Deploy."),
        ("src\\utils\\describe.ts", "utils", "Describe utility", "NONE", "LOW: Describe."),
        ("src\\utils\\desktop.ts", "utils", "Desktop utility", "NONE", "MEDIUM: Desktop."),
        ("src\\utils\\desktopLifecycle.ts", "utils", "Desktop lifecycle", "NONE", "MEDIUM: Desktop lifecycle."),
        ("src\\utils\\detectBinary.ts", "utils", "Detect binary", "NONE", "LOW: Binary detection."),
        ("src\\utils\\detectTerminal.ts", "utils", "Detect terminal", "NONE", "LOW: Terminal detection."),
        ("src\\utils\\developer.ts", "utils", "Developer utility", "NONE", "LOW: Developer."),
        ("src\\utils\\diff.ts", "utils", "Diff utility", "NONE", "MEDIUM: Diff."),
        ("src\\utils\\diffSummary.ts", "utils", "Diff summary", "NONE", "MEDIUM: Diff summary."),
        ("src\\utils\\digit.ts", "utils", "Digit utility", "NONE", "LOW: Digit."),
        ("src\\utils\\dir.ts", "utils", "Dir utility", "NONE", "LOW: Dir."),
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