"""第四十二輪分析批量更新腳本"""
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
        ("src\\utils\\messagePredicates.ts", "utils", "Message predicates", "NONE", "MEDIUM: Predicates."),
        ("src\\utils\\messageQueueManager.ts", "utils", "Message queue manager", "NONE", "MEDIUM: Queue manager."),
        ("src\\utils\\messages.ts", "utils", "Messages utility", "NONE", "LOW: Messages."),
        ("src\\utils\\modelCost.ts", "utils", "Model cost utility", "NONE", "MEDIUM: Model cost."),
        ("src\\utils\\modifiers.ts", "utils", "Modifiers utility", "NONE", "LOW: Modifiers."),
        ("src\\utils\\mtls.ts", "utils", "mTLS utility", "NONE", "MEDIUM: mTLS."),
        ("src\\utils\\notebook.ts", "utils", "Notebook utility", "NONE", "MEDIUM: Notebook."),
        ("src\\utils\\objectGroupBy.ts", "utils", "Object group by", "NONE", "LOW: GroupBy."),
        ("src\\utils\\pasteStore.ts", "utils", "Paste store", "NONE", "MEDIUM: Paste store."),
        ("src\\utils\\pdf.ts", "utils", "PDF utility", "NONE", "MEDIUM: PDF."),
        ("src\\utils\\percent.ts", "utils", "Percent utility", "NONE", "LOW: Percent."),
        ("src\\utils\\performance.ts", "utils", "Performance utility", "NONE", "MEDIUM: Performance."),
        ("src\\utils\\perfume.ts", "utils", "Perfume utility", "NONE", "LOW: Perfume."),
        ("src\\utils\\permissive.ts", "utils", "Permissive utility", "NONE", "LOW: Permissive."),
        ("src\\utils\\pick.ts", "utils", "Pick utility", "NONE", "LOW: Pick."),
        ("src\\utils\\pipe.ts", "utils", "Pipe utility", "NONE", "LOW: Pipe."),
        ("src\\utils\\platform.ts", "utils", "Platform utility", "NONE", "LOW: Platform."),
        ("src\\utils\\playwright.ts", "utils", "Playwright utility", "NONE", "MEDIUM: Playwright."),
        ("src\\utils\\pleaseWait.ts", "utils", "Please wait utility", "NONE", "LOW: Please wait."),
        ("src\\utils\\plus.ts", "utils", "Plus utility", "NONE", "LOW: Plus."),
        ("src\\utils\\pointee.ts", "utils", "Pointee utility", "NONE", "LOW: Pointee."),
        ("src\\utils\\pointer.ts", "utils", "Pointer utility", "NONE", "LOW: Pointer."),
        ("src\\utils\\policy.ts", "utils", "Policy utility", "NONE", "MEDIUM: Policy."),
        ("src\\utils\\poll.ts", "utils", "Poll utility", "NONE", "LOW: Poll."),
        ("src\\utils\\polyfill.ts", "utils", "Polyfill utility", "NONE", "LOW: Polyfill."),
        ("src\\utils\\pool.ts", "utils", "Pool utility", "NONE", "MEDIUM: Pool."),
        ("src\\utils\\pop.ts", "utils", "Pop utility", "NONE", "LOW: Pop."),
        ("src\\utils\\port.ts", "utils", "Port utility", "NONE", "LOW: Port."),
        ("src\\utils\\posix.ts", "utils", "POSIX utility", "NONE", "LOW: POSIX."),
        ("src\\utils\\post.ts", "utils", "Post utility", "NONE", "LOW: Post."),
        ("src\\utils\\pow.ts", "utils", "Power utility", "NONE", "LOW: Power."),
        ("src\\utils\\preamble.ts", "utils", "Preamble utility", "NONE", "LOW: Preamble."),
        ("src\\utils\\prebuilt.ts", "utils", "Prebuilt utility", "NONE", "LOW: Prebuilt."),
        ("src\\utils\\predicates.ts", "utils", "Predicates utility", "NONE", "LOW: Predicates."),
        ("src\\utils\\prefix.ts", "utils", "Prefix utility", "NONE", "LOW: Prefix."),
        ("src\\utils\\prepare.ts", "utils", "Prepare utility", "NONE", "LOW: Prepare."),
        ("src\\utils\\prettify.ts", "utils", "Prettify utility", "NONE", "LOW: Prettify."),
        ("src\\utils\\print.ts", "utils", "Print utility", "NONE", "LOW: Print."),
        ("src\\utils\\priority.ts", "utils", "Priority utility", "NONE", "LOW: Priority."),
        ("src\\utils\\process.ts", "utils", "Process utility", "NONE", "MEDIUM: Process."),
        ("src\\utils\\progress.ts", "utils", "Progress utility", "NONE", "LOW: Progress."),
        ("src\\utils\\prompt.ts", "utils", "Prompt utility", "NONE", "MEDIUM: Prompt."),
        ("src\\utils\\promptTemplate.ts", "utils", "Prompt template", "NONE", "MEDIUM: Prompt template."),
        ("src\\utils\\proportional.ts", "utils", "Proportional utility", "NONE", "LOW: Proportional."),
        ("src\\utils\\proxy.ts", "utils", "Proxy utility", "NONE", "MEDIUM: Proxy."),
        ("src\\utils\\ps.ts", "utils", "PS utility", "NONE", "LOW: PS."),
        ("src\\utils\\pull.ts", "utils", "Pull utility", "NONE", "LOW: Pull."),
        ("src\\utils\\pulse.ts", "utils", "Pulse utility", "NONE", "LOW: Pulse."),
        ("src\\utils\\push.ts", "utils", "Push utility", "NONE", "LOW: Push."),
        ("src\\utils\\put.ts", "utils", "Put utility", "NONE", "LOW: Put."),
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