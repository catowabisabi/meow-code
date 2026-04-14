"""第三十一輪分析批量更新腳本 - utils 目錄大量更新"""
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
        ("src\\utils\\backgroundHousekeeping.ts", "utils", "Background housekeeping", "NONE", "MEDIUM: Housekeeping."),
        ("src\\utils\\betas.ts", "utils", "Beta features utility", "NONE", "LOW: Beta."),
        ("src\\utils\\billing.ts", "utils", "Billing utility", "NONE", "MEDIUM: Billing."),
        ("src\\utils\\binaryCheck.ts", "utils", "Binary check", "NONE", "LOW: Binary check."),
        ("src\\utils\\bundledMode.ts", "utils", "Bundled mode detection", "NONE", "LOW: Bundled mode."),
        ("src\\utils\\caCerts.ts", "utils", "CA certificates", "NONE", "MEDIUM: CA certs."),
        ("src\\utils\\caCertsConfig.ts", "utils", "CA certs config", "NONE", "MEDIUM: CA certs config."),
        ("src\\utils\\cachePaths.ts", "utils", "Cache paths", "NONE", "MEDIUM: Cache paths."),
        ("src\\utils\\CircularBuffer.ts", "utils", "Circular buffer", "NONE", "LOW: Circular buffer."),
        ("src\\utils\\classifierApprovals.ts", "utils", "Classifier approvals", "NONE", "HIGH: Classifier."),
        ("src\\utils\\cleanup.ts", "utils", "Cleanup utility", "NONE", "LOW: Cleanup."),
        ("src\\utils\\client.ts", "utils", "Client utility", "NONE", "MEDIUM: Client."),
        ("src\\utils\\clipboardManager.ts", "utils", "Clipboard manager", "NONE", "MEDIUM: Clipboard."),
        ("src\\utils\\cloud.ts", "utils", "Cloud utility", "NONE", "MEDIUM: Cloud."),
        ("src\\utils\\cluster.ts", "utils", "Cluster utility", "NONE", "MEDIUM: Cluster."),
        ("src\\utils\\cmdline.ts", "utils", "Command line utility", "NONE", "MEDIUM: Cmdline."),
        ("src\\utils\\codeBlock.ts", "utils", "Code block utility", "NONE", "LOW: Code block."),
        ("src\\utils\\codesign.ts", "utils", "Code sign utility", "NONE", "LOW: Code sign."),
        ("src\\utils\\color.ts", "utils", "Color utility", "NONE", "LOW: Color."),
        ("src\\utils\\compact.ts", "utils", "Compact utility", "NONE", "LOW: Compact."),
        ("src\\utils\\compare.ts", "utils", "Compare utility", "NONE", "LOW: Compare."),
        ("src\\utils\\compile.ts", "utils", "Compile utility", "NONE", "LOW: Compile."),
        ("src\\utils\\complete.ts", "utils", "Complete utility", "NONE", "LOW: Complete."),
        ("src\\utils\\concat.ts", "utils", "Concat utility", "NONE", "LOW: Concat."),
        ("src\\utils\\concurrent.ts", "utils", "Concurrent utility", "NONE", "LOW: Concurrent."),
        ("src\\utils\\conditionVariable.ts", "utils", "Condition variable", "NONE", "LOW: Condvar."),
        ("src\\utils\\config.ts", "utils", "Config utility", "NONE", "MEDIUM: Config."),
        ("src\\utils\\configure.ts", "utils", "Configure utility", "NONE", "MEDIUM: Configure."),
        ("src\\utils\\confirm.ts", "utils", "Confirm utility", "NONE", "LOW: Confirm."),
        ("src\\utils\\connection.ts", "utils", "Connection utility", "NONE", "MEDIUM: Connection."),
        ("src\\utils\\console.ts", "utils", "Console utility", "NONE", "LOW: Console."),
        ("src\\utils\\constant.ts", "utils", "Constant utility", "NONE", "LOW: Constant."),
        ("src\\utils\\context.ts", "utils", "Context utility", "NONE", "MEDIUM: Context."),
        ("src\\utils\\control.ts", "utils", "Control utility", "NONE", "LOW: Control."),
        ("src\\utils\\convert.ts", "utils", "Convert utility", "NONE", "LOW: Convert."),
        ("src\\utils\\cookie.ts", "utils", "Cookie utility", "NONE", "MEDIUM: Cookie."),
        ("src\\utils\\count.ts", "utils", "Count utility", "NONE", "LOW: Count."),
        ("src\\utils\\counter.ts", "utils", "Counter utility", "NONE", "LOW: Counter."),
        ("src\\utils\\crash.ts", "utils", "Crash utility", "NONE", "MEDIUM: Crash."),
        ("src\\utils\\createDir.ts", "utils", "Create directory", "NONE", "LOW: Create dir."),
        ("src\\utils\\crypto.ts", "utils", "Crypto utility", "NONE", "MEDIUM: Crypto."),
        ("src\\utils\\curl.ts", "utils", "Curl utility", "NONE", "MEDIUM: Curl."),
        ("src\\utils\\currentDate.ts", "utils", "Current date utility", "NONE", "LOW: Current date."),
        ("src\\utils\\customer.ts", "utils", "Customer utility", "NONE", "MEDIUM: Customer."),
        ("src\\utils\\datasource.ts", "utils", "Datasource utility", "NONE", "MEDIUM: Datasource."),
        ("src\\utils\\datetime.ts", "utils", "Datetime utility", "NONE", "LOW: Datetime."),
        ("src\\utils\\day.ts", "utils", "Day utility", "NONE", "LOW: Day."),
        ("src\\utils\\dbox.ts", "utils", "Dbox utility", "NONE", "LOW: Dbox."),
        ("src\\utils\\debug.ts", "utils", "Debug utility", "NONE", "LOW: Debug."),
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