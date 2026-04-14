"""第二十七輪分析批量更新腳本 - services, tasks, tools"""
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
        ("src\\keybindings\\validate.ts", "keybindings", "Keybinding validation", "NONE", "LOW: Validation."),
        ("src\\services\\claudeAiLimitsHook.ts", "services", "Claude AI limits hook", "NONE", "MEDIUM: Rate limiting."),
        ("src\\services\\internalLogging.ts", "services", "Internal logging service", "NONE", "MEDIUM: Logging."),
        ("src\\services\\mockRateLimits.ts", "services", "Mock rate limits", "NONE", "MEDIUM: Rate limiting."),
        ("src\\services\\preventSleep.ts", "services", "Prevent sleep service", "NONE", "MEDIUM: Power management."),
        ("src\\services\\rateLimitMocking.ts", "services", "Rate limit mocking", "NONE", "MEDIUM: Rate limiting."),
        ("src\\services\\vcr.ts", "services", "VCR service", "NONE", "MEDIUM: VCR/Cassette."),
        ("src\\tasks\\pillLabel.ts", "tasks", "Pill label task", "NONE", "LOW: UI task."),
        ("src\\tools\\utils.ts", "tools", "Tools utility functions", "NONE", "MEDIUM: Tool utils."),
        ("src\\utils\\abortController.ts", "utils", "AbortController utils", "NONE", "LOW: Abort controller."),
        ("src\\utils\\analytics.ts", "utils", "Analytics utils", "NONE", "MEDIUM: Analytics."),
        ("src\\utils\\assert.ts", "utils", "Assertion utils", "NONE", "LOW: Assert."),
        ("src\\utils\\async.ts", "utils", "Async utilities", "NONE", "LOW: Async."),
        ("src\\utils\\base64.ts", "utils", "Base64 encoding", "NONE", "LOW: Encoding."),
        ("src\\utils\\checkOwnership.ts", "utils", "Check ownership", "NONE", "MEDIUM: Ownership."),
        ("src\\utils\\cli.ts", "utils", "CLI utilities", "NONE", "MEDIUM: CLI."),
        ("src\\utils\\cmdq.ts", "utils", "Command queue", "NONE", "MEDIUM: Queue."),
        ("src\\utils\\colors.ts", "utils", "Color utilities", "NONE", "LOW: Colors."),
        ("src\\utils\\compact-string.ts", "utils", "Compact string", "NONE", "LOW: String."),
        ("src\\utils\\condition.ts", "utils", "Condition utilities", "NONE", "LOW: Condition."),
        ("src\\utils\\connect.ts", "utils", "Connection utilities", "NONE", "MEDIUM: Connection."),
        ("src\\utils\\convert.ts", "utils", "Conversion utilities", "NONE", "LOW: Convert."),
        ("src\\utils\\dasherize.ts", "utils", "Dasherize string", "NONE", "LOW: String."),
        ("src\\utils\\debug.ts", "utils", "Debug utilities", "NONE", "LOW: Debug."),
        ("src\\utils\\deep-equal.ts", "utils", "Deep equality check", "NONE", "LOW: Equality."),
        ("src\\utils\\deep-merge.ts", "utils", "Deep merge", "NONE", "LOW: Merge."),
        ("src\\utils\\delay.ts", "utils", "Delay utility", "NONE", "LOW: Delay."),
        ("src\\utils\\dependency.ts", "utils", "Dependency utilities", "NONE", "LOW: Dependency."),
        ("src\\utils\\difference.ts", "utils", "Difference utility", "NONE", "LOW: Diff."),
        ("src\\utils\\digit.ts", "utils", "Digit utilities", "NONE", "LOW: Digit."),
        ("src\\utils\\dirname.ts", "utils", "Directory name utility", "NONE", "LOW: Dirname."),
        ("src\\utils\\dispose.ts", "utils", "Dispose utilities", "NONE", "LOW: Dispose."),
        ("src\\utils\DNA.ts", "utils", "DNA utilities", "NONE", "LOW: DNA."),
        ("src\\utils\\download.ts", "utils", "Download utility", "NONE", "MEDIUM: Download."),
        ("src\\utils\\dump.ts", "utils", "Dump utilities", "NONE", "LOW: Dump."),
        ("src\\utils\\errors.ts", "utils", "Error utilities", "NONE", "LOW: Errors."),
        ("src\\utils\\escape.ts", "utils", "Escape utilities", "NONE", "LOW: Escape."),
        ("src\\utils\\execute.ts", "utils", "Execute utilities", "NONE", "MEDIUM: Execute."),
        ("src\\utils\\exit.ts", "utils", "Exit utilities", "NONE", "LOW: Exit."),
        ("src\\utils\\expand.ts", "utils", "Expand utilities", "NONE", "LOW: Expand."),
        ("src\\utils\\explain.ts", "utils", "Explain utilities", "NONE", "LOW: Explain."),
        ("src\\utils\\filter-object.ts", "utils", "Filter object", "NONE", "LOW: Filter."),
        ("src\\utils\\find-buffer.ts", "utils", "Find buffer", "NONE", "LOW: Buffer."),
        ("src\\utils\\find-line.ts", "utils", "Find line", "NONE", "LOW: Find."),
        ("src\\utils\\flat.ts", "utils", "Flat utilities", "NONE", "LOW: Flat."),
        ("src\\utils\\flatpak.ts", "utils", "Flatpak utilities", "NONE", "LOW: Flatpak."),
        ("src\\utils\\fn.ts", "utils", "Function utilities", "NONE", "LOW: Fn."),
        ("src\\utils\\format.ts", "utils", "Format utilities", "NONE", "LOW: Format."),
        ("src\\utils\\fs.ts", "utils", "Filesystem utilities", "NONE", "MEDIUM: FS."),
        ("src\\utils\\getHostname.ts", "utils", "Get hostname", "NONE", "LOW: Hostname."),
        ("src\\utils\\git.ts", "utils", "Git utilities", "NONE", "MEDIUM: Git."),
        ("src\\utils\\groupBy.ts", "utils", "Group by", "NONE", "LOW: GroupBy."),
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