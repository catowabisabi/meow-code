"""第三十八輪分析批量更新腳本"""
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
        ("src\\utils\\getWorktreePathsPortable.ts", "utils", "Get worktree paths portable", "NONE", "HIGH: Worktree portable."),
        ("src\\utils\\ghPrStatus.ts", "utils", "GitHub PR status", "NONE", "MEDIUM: PR status."),
        ("src\\utils\\githubRepoPathMapping.ts", "utils", "GitHub repo path mapping", "NONE", "MEDIUM: Repo mapping."),
        ("src\\utils\\gitSettings.ts", "utils", "Git settings", "NONE", "MEDIUM: Git settings."),
        ("src\\utils\\glob.ts", "utils", "Glob utility", "NONE", "LOW: Glob."),
        ("src\\utils\\gracefulShutdown.ts", "utils", "Graceful shutdown", "NONE", "MEDIUM: Shutdown."),
        ("src\\utils\\groupToolUses.ts", "utils", "Group tool uses", "NONE", "MEDIUM: Tool grouping."),
        ("src\\utils\\handlePromptSubmit.ts", "utils", "Handle prompt submit", "NONE", "MEDIUM: Prompt handling."),
        ("src\\utils\\headlessProfiler.ts", "utils", "Headless profiler", "NONE", "MEDIUM: Profiler."),
        ("src\\utils\\heapDumpService.ts", "utils", "Heap dump service", "NONE", "MEDIUM: Heap dump."),
        ("src\\utils\\hmac.ts", "utils", "HMAC utility", "NONE", "MEDIUM: HMAC."),
        ("src\\utils\\host.ts", "utils", "Host utility", "NONE", "LOW: Host."),
        ("src\\utils\\hostname.ts", "utils", "Hostname utility", "NONE", "LOW: Hostname."),
        ("src\\utils\\hours.ts", "utils", "Hours utility", "NONE", "LOW: Hours."),
        ("src\\utils\\humanize.ts", "utils", "Humanize utility", "NONE", "LOW: Humanize."),
        ("src\\utils\\id.ts", "utils", "ID utility", "NONE", "LOW: ID."),
        ("src\\utils\\identity.ts", "utils", "Identity utility", "NONE", "LOW: Identity."),
        ("src\\utils\\ignore.ts", "utils", "Ignore utility", "NONE", "LOW: Ignore."),
        ("src\\utils\\image.ts", "utils", "Image utility", "NONE", "LOW: Image."),
        ("src\\utils\\imageUrl.ts", "utils", "Image URL utility", "NONE", "LOW: Image URL."),
        ("src\\utils\\imap.ts", "utils", "IMAP utility", "NONE", "MEDIUM: IMAP."),
        ("src\\utils\\immutable.ts", "utils", "Immutable utility", "NONE", "LOW: Immutable."),
        ("src\\utils\\implies.ts", "utils", "Implies utility", "NONE", "LOW: Implies."),
        ("src\\utils\\inCato.ts", "utils", "In Cato check", "NONE", "LOW: Cato check."),
        ("src\\utils\\inDirectory.ts", "utils", "In directory check", "NONE", "LOW: Directory check."),
        ("src\\utils\\index.ts", "utils", "Index utility", "NONE", "LOW: Index."),
        ("src\\utils\\init.ts", "utils", "Init utility", "NONE", "LOW: Init."),
        ("src\\utils\\initial.ts", "utils", "Initial utility", "NONE", "LOW: Initial."),
        ("src\\utils\\inline.ts", "utils", "Inline utility", "NONE", "LOW: Inline."),
        ("src\\utils\\input.ts", "utils", "Input utility", "NONE", "LOW: Input."),
        ("src\\utils\\inputPrompt.ts", "utils", "Input prompt", "NONE", "LOW: Input prompt."),
        ("src\\utils\\insert.ts", "utils", "Insert utility", "NONE", "LOW: Insert."),
        ("src\\utils\\inspect.ts", "utils", "Inspect utility", "NONE", "LOW: Inspect."),
        ("src\\utils\\instance.ts", "utils", "Instance utility", "NONE", "LOW: Instance."),
        ("src\\utils\\int.ts", "utils", "Int utility", "NONE", "LOW: Int."),
        ("src\\utils\\integer.ts", "utils", "Integer utility", "NONE", "LOW: Integer."),
        ("src\\utils\\interact.ts", "utils", "Interact utility", "NONE", "MEDIUM: Interact."),
        ("src\\utils\\interface.ts", "utils", "Interface utility", "NONE", "LOW: Interface."),
        ("src\\utils\\interval.ts", "utils", "Interval utility", "NONE", "LOW: Interval."),
        ("src\\utils\\interpolate.ts", "utils", "Interpolate utility", "NONE", "LOW: Interpolate."),
        ("src\\utils\\intersect.ts", "utils", "Intersect utility", "NONE", "LOW: Intersect."),
        ("src\\utils\\intersection.ts", "utils", "Intersection utility", "NONE", "LOW: Intersection."),
        ("src\\utils\\intervalMap.ts", "utils", "Interval map", "NONE", "LOW: Interval map."),
        ("src\\utils\\into.ts", "utils", "Into utility", "NONE", "LOW: Into."),
        ("src\\utils\\invalid.ts", "utils", "Invalid utility", "NONE", "LOW: Invalid."),
        ("src\\utils\\invoke.ts", "utils", "Invoke utility", "NONE", "LOW: Invoke."),
        ("src\\utils\\invokeFunction.ts", "utils", "Invoke function", "NONE", "LOW: Invoke function."),
        ("src\\utils\\io.ts", "utils", "IO utility", "NONE", "MEDIUM: IO."),
        ("src\\utils\\ip.ts", "utils", "IP utility", "NONE", "LOW: IP."),
        ("src\\utils\\is.ts", "utils", "Is utility", "NONE", "LOW: Is."),
        ("src\\utils\\isAppleTerminal.ts", "utils", "Is Apple Terminal", "NONE", "LOW: Apple Terminal."),
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