"""第三十二輪分析批量更新腳本"""
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
        ("src\\utils\\classifierApprovalsHook.ts", "utils", "Classifier approvals hook", "NONE", "HIGH: Classifier hook."),
        ("src\\utils\\claudeCodeHints.ts", "utils", "Claude Code hints", "NONE", "LOW: Hints."),
        ("src\\utils\\claudeDesktop.ts", "utils", "Claude Desktop integration", "NONE", "MEDIUM: Desktop."),
        ("src\\utils\\claudemd.ts", "utils", "Claude md utility", "NONE", "LOW: Markdown."),
        ("src\\utils\\cliArgs.ts", "utils", "CLI arguments", "NONE", "MEDIUM: CLI args."),
        ("src\\utils\\cliHighlight.ts", "utils", "CLI highlighting", "NONE", "LOW: Highlight."),
        ("src\\utils\\codeIndexing.ts", "utils", "Code indexing", "NONE", "MEDIUM: Indexing."),
        ("src\\utils\\collapseBackgroundBashNotifications.ts", "utils", "Collapse bash notifications", "NONE", "LOW: Notifications."),
        ("src\\utils\\collapseHookSummaries.ts", "utils", "Collapse hook summaries", "NONE", "LOW: Hook summaries."),
        ("src\\utils\\collapseReadSearch.ts", "utils", "Collapse read search", "NONE", "LOW: Search."),
        ("src\\utils\\combine.ts", "utils", "Combine utility", "NONE", "LOW: Combine."),
        ("src\\utils\\command.ts", "utils", "Command utility", "NONE", "MEDIUM: Command."),
        ("src\\utils\\commandBar.ts", "utils", "Command bar", "NONE", "LOW: Command bar."),
        ("src\\utils\\commandLine.ts", "utils", "Command line", "NONE", "MEDIUM: Cmdline."),
        ("src\\utils\\comments.ts", "utils", "Comments utility", "NONE", "LOW: Comments."),
        ("src\\utils\\compactIt.ts", "utils", "Compact iterator", "NONE", "LOW: Iterator."),
        ("src\\utils\\compareVersions.ts", "utils", "Compare versions", "NONE", "LOW: Version compare."),
        ("src\\utils\\compat.ts", "utils", "Compatibility utility", "NONE", "LOW: Compat."),
        ("src\\utils\\concat.ts", "utils", "Concat utility", "NONE", "LOW: Concat."),
        ("src\\utils\\concatenate.ts", "utils", "Concatenate utility", "NONE", "LOW: Concatenate."),
        ("src\\utils\\condition.ts", "utils", "Condition utility", "NONE", "LOW: Condition."),
        ("src\\utils\\config.ts", "utils", "Config utility", "NONE", "MEDIUM: Config."),
        ("src\\utils\\constants.ts", "utils", "Constants", "NONE", "LOW: Constants."),
        ("src\\utils\\contains.ts", "utils", "Contains utility", "NONE", "LOW: Contains."),
        ("src\\utils\\content.ts", "utils", "Content utility", "NONE", "LOW: Content."),
        ("src\\utils\\contents.ts", "utils", "Contents utility", "NONE", "LOW: Contents."),
        ("src\\utils\\context.ts", "utils", "Context utility", "NONE", "MEDIUM: Context."),
        ("src\\utils\\contract.ts", "utils", "Contract utility", "NONE", "LOW: Contract."),
        ("src\\utils\\conversation.ts", "utils", "Conversation utility", "NONE", "MEDIUM: Conversation."),
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