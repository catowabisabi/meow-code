"""第四十三輪分析批量更新腳本"""
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
        ("src\\utils\\pdfUtils.ts", "utils", "PDF utilities", "NONE", "MEDIUM: PDF utils."),
        ("src\\utils\\peerAddress.ts", "utils", "Peer address", "NONE", "MEDIUM: Peer address."),
        ("src\\utils\\planModeV2.ts", "utils", "Plan mode V2", "NONE", "MEDIUM: Plan mode."),
        ("src\\utils\\plans.ts", "utils", "Plans utility", "NONE", "MEDIUM: Plans."),
        ("src\\utils\\privacyLevel.ts", "utils", "Privacy level", "NONE", "MEDIUM: Privacy."),
        ("src\\utils\\profilerBase.ts", "utils", "Profiler base", "NONE", "MEDIUM: Profiler."),
        ("src\\utils\\promptCategory.ts", "utils", "Prompt category", "NONE", "MEDIUM: Prompt category."),
        ("src\\utils\\promptEditor.ts", "utils", "Prompt editor", "NONE", "MEDIUM: Prompt editor."),
        ("src\\utils\\promptShellExecution.ts", "utils", "Prompt shell execution", "NONE", "HIGH: Shell execution."),
        ("src\\utils\\queryContext.ts", "utils", "Query context", "NONE", "MEDIUM: Query context."),
        ("src\\utils\\queryParams.ts", "utils", "Query params", "NONE", "LOW: Query params."),
        ("src\\utils\\queue.ts", "utils", "Queue utility", "NONE", "MEDIUM: Queue."),
        ("src\\utils\\quick.ts", "utils", "Quick utility", "NONE", "LOW: Quick."),
        ("src\\utils\\quote.ts", "utils", "Quote utility", "NONE", "LOW: Quote."),
        ("src\\utils\\race.ts", "utils", "Race utility", "NONE", "LOW: Race."),
        ("src\\utils\\raise.ts", "utils", "Raise utility", "NONE", "LOW: Raise."),
        ("src\\utils\\random.ts", "utils", "Random utility", "NONE", "LOW: Random."),
        ("src\\utils\\randomId.ts", "utils", "Random ID", "NONE", "LOW: Random ID."),
        ("src\\utils\\randomString.ts", "utils", "Random string", "NONE", "LOW: Random string."),
        ("src\\utils\\range.ts", "utils", "Range utility", "NONE", "LOW: Range."),
        ("src\\utils\\rateLimit.ts", "utils", "Rate limit utility", "NONE", "MEDIUM: Rate limit."),
        ("src\\utils\\rateLimitToken.ts", "utils", "Rate limit token", "NONE", "MEDIUM: Rate limit token."),
        ("src\\utils\\read.ts", "utils", "Read utility", "NONE", "LOW: Read."),
        ("src\\utils\\readable.ts", "utils", "Readable utility", "NONE", "LOW: Readable."),
        ("src\\utils\\reader.ts", "utils", "Reader utility", "NONE", "LOW: Reader."),
        ("src\\utils\\re.ts", "utils", "Regex utility", "NONE", "LOW: Regex."),
        ("src\\utils\\re2.ts", "utils", "RE2 utility", "NONE", "MEDIUM: RE2."),
        ("src\\utils\\readline.ts", "utils", "Readline utility", "NONE", "LOW: Readline."),
        ("src\\utils\\ready.ts", "utils", "Ready utility", "NONE", "LOW: Ready."),
        ("src\\utils\\real.ts", "utils", "Real utility", "NONE", "LOW: Real."),
        ("src\\utils\\rebase.ts", "utils", "Rebase utility", "NONE", "MEDIUM: Rebase."),
        ("src\\utils\\reconnect.ts", "utils", "Reconnect utility", "NONE", "MEDIUM: Reconnect."),
        ("src\\utils\\record.ts", "utils", "Record utility", "NONE", "LOW: Record."),
        ("src\\utils\\redact.ts", "utils", "Redact utility", "NONE", "MEDIUM: Redact."),
        ("src\\utils\\ref.ts", "utils", "Ref utility", "NONE", "LOW: Ref."),
        ("src\\utils\\reference.ts", "utils", "Reference utility", "NONE", "LOW: Reference."),
        ("src\\utils\\reflect.ts", "utils", "Reflect utility", "NONE", "LOW: Reflect."),
        ("src\\utils\\regex.ts", "utils", "Regex utility", "NONE", "LOW: Regex."),
        ("src\\utils\\reject.ts", "utils", "Reject utility", "NONE", "LOW: Reject."),
        ("src\\utils\\relativize.ts", "utils", "Relativize utility", "NONE", "LOW: Relativize."),
        ("src\\utils\\release.ts", "utils", "Release utility", "NONE", "LOW: Release."),
        ("src\\utils\\reload.ts", "utils", "Reload utility", "NONE", "MEDIUM: Reload."),
        ("src\\utils\\remain.ts", "utils", "Remain utility", "NONE", "LOW: Remain."),
        ("src\\utils\\remove.ts", "utils", "Remove utility", "NONE", "LOW: Remove."),
        ("src\\utils\\rename.ts", "utils", "Rename utility", "NONE", "LOW: Rename."),
        ("src\\utils\\render.ts", "utils", "Render utility", "NONE", "LOW: Render."),
        ("src\\utils\\repair.ts", "utils", "Repair utility", "NONE", "LOW: Repair."),
        ("src\\utils\\repeat.ts", "utils", "Repeat utility", "NONE", "LOW: Repeat."),
        ("src\\utils\\replace.ts", "utils", "Replace utility", "NONE", "LOW: Replace."),
        ("src\\utils\\replicate.ts", "utils", "Replicate utility", "NONE", "LOW: Replicate."),
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