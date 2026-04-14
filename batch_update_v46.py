"""第四十六輪分析批量更新腳本"""
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
        ("src\\utils\\sessionUrl.ts", "utils", "Session URL", "NONE", "MEDIUM: Session URL."),
        ("src\\utils\\ShellCommand.ts", "utils", "Shell command utility", "NONE", "MEDIUM: Shell command."),
        ("src\\utils\\shellConfig.ts", "utils", "Shell config", "NONE", "MEDIUM: Shell config."),
        ("src\\utils\\sideQuery.ts", "utils", "Side query", "NONE", "MEDIUM: Side query."),
        ("src\\utils\\sideQuestion.ts", "utils", "Side question", "NONE", "MEDIUM: Side question."),
        ("src\\utils\\sinks.ts", "utils", "Sinks utility", "NONE", "LOW: Sinks."),
        ("src\\utils\\slashCommandParsing.ts", "utils", "Slash command parsing", "NONE", "MEDIUM: Slash commands."),
        ("src\\utils\\sliceAnsi.ts", "utils", "Slice ANSI", "NONE", "LOW: ANSI slice."),
        ("src\\utils\\slowOperations.ts", "utils", "Slow operations tracking", "NONE", "MEDIUM: Slow ops."),
        ("src\\utils\\standaloneAgent.ts", "utils", "Standalone agent", "NONE", "HIGH: Standalone agent."),
        ("src\\utils\\startsWith.ts", "utils", "Starts with utility", "NONE", "LOW: Starts with."),
        ("src\\utils\\state.ts", "utils", "State utility", "NONE", "MEDIUM: State."),
        ("src\\utils\\stateful.ts", "utils", "Stateful utility", "NONE", "LOW: Stateful."),
        ("src\\utils\\status.ts", "utils", "Status utility", "NONE", "LOW: Status."),
        ("src\\utils\\statusCode.ts", "utils", "Status code utility", "NONE", "LOW: Status code."),
        ("src\\utils\\stdin.ts", "utils", "Stdin utility", "NONE", "LOW: Stdin."),
        ("src\\utils\\step.ts", "utils", "Step utility", "NONE", "LOW: Step."),
        ("src\\utils\\stopwatch.ts", "utils", "Stopwatch utility", "NONE", "LOW: Stopwatch."),
        ("src\\utils\\store.ts", "utils", "Store utility", "NONE", "MEDIUM: Store."),
        ("src\\utils\\string.ts", "utils", "String utility", "NONE", "LOW: String."),
        ("src\\utils\\stringify.ts", "utils", "Stringify utility", "NONE", "LOW: Stringify."),
        ("src\\utils\\stringWidth.ts", "utils", "String width utility", "NONE", "LOW: String width."),
        ("src\\utils\\strip.ts", "utils", "Strip utility", "NONE", "LOW: Strip."),
        ("src\\utils\\stripsAnsi.ts", "utils", "Strip ANSI utility", "NONE", "LOW: Strip ANSI."),
        ("src\\utils\\struct.ts", "utils", "Struct utility", "NONE", "LOW: Struct."),
        ("src\\utils\\style.ts", "utils", "Style utility", "NONE", "LOW: Style."),
        ("src\\utils\\subject.ts", "utils", "Subject utility", "NONE", "LOW: Subject."),
        ("src\\utils\\subscribe.ts", "utils", "Subscribe utility", "NONE", "LOW: Subscribe."),
        ("src\\utils\\substring.ts", "utils", "Substring utility", "NONE", "LOW: Substring."),
        ("src\\utils\\sum.ts", "utils", "Sum utility", "NONE", "LOW: Sum."),
        ("src\\utils\\summary.ts", "utils", "Summary utility", "NONE", "LOW: Summary."),
        ("src\\utils\\super.ts", "utils", "Super utility", "NONE", "LOW: Super."),
        ("src\\utils\\suppress.ts", "utils", "Suppress utility", "NONE", "LOW: Suppress."),
        ("src\\utils\\suspend.ts", "utils", "Suspend utility", "NONE", "LOW: Suspend."),
        ("src\\utils\\swap.ts", "utils", "Swap utility", "NONE", "LOW: Swap."),
        ("src\\utils\\symbol.ts", "utils", "Symbol utility", "NONE", "LOW: Symbol."),
        ("src\\utils\\sync.ts", "utils", "Sync utility", "NONE", "LOW: Sync."),
        ("src\\utils\\syntax.ts", "utils", "Syntax utility", "NONE", "LOW: Syntax."),
        ("src\\utils\\system.ts", "utils", "System utility", "NONE", "MEDIUM: System."),
        ("src\\utils\\systemInfo.ts", "utils", "System info", "NONE", "MEDIUM: System info."),
        ("src\\utils\\tab.ts", "utils", "Tab utility", "NONE", "LOW: Tab."),
        ("src\\utils\\table.ts", "utils", "Table utility", "NONE", "LOW: Table."),
        ("src\\utils\\tail.ts", "utils", "Tail utility", "NONE", "LOW: Tail."),
        ("src\\utils\\take.ts", "utils", "Take utility", "NONE", "LOW: Take."),
        ("src\\utils\\tap.ts", "utils", "Tap utility", "NONE", "LOW: Tap."),
        ("src\\utils\\task.ts", "utils", "Task utility", "NONE", "MEDIUM: Task."),
        ("src\\utils\\taskId.ts", "utils", "Task ID utility", "NONE", "LOW: Task ID."),
        ("src\\utils\\temp.ts", "utils", "Temp utility", "NONE", "LOW: Temp."),
        ("src\\utils\\template.ts", "utils", "Template utility", "NONE", "LOW: Template."),
        ("src\\utils\\temporaryFile.ts", "utils", "Temporary file", "NONE", "MEDIUM: Temp file."),
        ("src\\utils\\terminal.ts", "utils", "Terminal utility", "NONE", "MEDIUM: Terminal."),
        ("src\\utils\\test.ts", "utils", "Test utility", "NONE", "LOW: Test."),
        ("src\\utils\\teammate.ts", "utils", "Teammate utility", "NONE", "HIGH: Teammate."),
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