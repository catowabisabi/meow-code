"""第四十八輪分析批量更新腳本"""
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
        ("src\\utils\\systemTheme.ts", "utils", "System theme", "NONE", "LOW: System theme."),
        ("src\\utils\\taggedId.ts", "utils", "Tagged ID", "NONE", "LOW: Tagged ID."),
        ("src\\utils\\tasks.ts", "utils", "Tasks utility", "NONE", "MEDIUM: Tasks."),
        ("src\\utils\\teamDiscovery.ts", "utils", "Team discovery", "NONE", "HIGH: Team discovery."),
        ("src\\utils\\teammateMailbox.ts", "utils", "Teammate mailbox", "NONE", "HIGH: Teammate mailbox."),
        ("src\\utils\\teamMemoryOps.ts", "utils", "Team memory operations", "NONE", "HIGH: Team memory."),
        ("src\\utils\\telemetryAttributes.ts", "utils", "Telemetry attributes", "NONE", "MEDIUM: Telemetry."),
        ("src\\utils\\tempfile.ts", "utils", "Tempfile utility", "NONE", "LOW: Tempfile."),
        ("src\\utils\\textHighlighting.ts", "utils", "Text highlighting", "NONE", "LOW: Highlighting."),
        ("src\\utils\\theme.ts", "utils", "Theme utility", "NONE", "LOW: Theme."),
        ("src\\utils\\then.ts", "utils", "Then utility", "NONE", "LOW: Then."),
        ("src\\utils\\thenBy.ts", "utils", "Then by utility", "NONE", "LOW: ThenBy."),
        ("src\\utils\\throttle.ts", "utils", "Throttle utility", "NONE", "LOW: Throttle."),
        ("src\\utils\\through.ts", "utils", "Through utility", "NONE", "LOW: Through."),
        ("src\\utils\\throw.ts", "utils", "Throw utility", "NONE", "LOW: Throw."),
        ("src\\utils\\tick.ts", "utils", "Tick utility", "NONE", "LOW: Tick."),
        ("src\\utils\\tilde.ts", "utils", "Tilde utility", "NONE", "LOW: Tilde."),
        ("src\\utils\\time.ts", "utils", "Time utility", "NONE", "LOW: Time."),
        ("src\\utils\\timeout.ts", "utils", "Timeout utility", "NONE", "LOW: Timeout."),
        ("src\\utils\\timer.ts", "utils", "Timer utility", "NONE", "LOW: Timer."),
        ("src\\utils\\timestamp.ts", "utils", "Timestamp utility", "NONE", "LOW: Timestamp."),
        ("src\\utils\\title.ts", "utils", "Title utility", "NONE", "LOW: Title."),
        ("src\\utils\\tmp.ts", "utils", "Tmp utility", "NONE", "LOW: Tmp."),
        ("src\\utils\\to.ts", "utils", "To utility", "NONE", "LOW: To."),
        ("src\\utils\\toggle.ts", "utils", "Toggle utility", "NONE", "LOW: Toggle."),
        ("src\\utils\\token.ts", "utils", "Token utility", "NONE", "MEDIUM: Token."),
        ("src\\utils\\tokenizer.ts", "utils", "Tokenizer utility", "NONE", "LOW: Tokenizer."),
        ("src\\utils\\toml.ts", "utils", "TOML utility", "NONE", "LOW: TOML."),
        ("src\\utils\\tonumber.ts", "utils", "To number utility", "NONE", "LOW: To number."),
        ("src\\utils\\tool.ts", "utils", "Tool utility", "NONE", "MEDIUM: Tool."),
        ("src\\utils\\toolExec.ts", "utils", "Tool exec utility", "NONE", "HIGH: Tool exec."),
        ("src\\utils\\toolUse.ts", "utils", "Tool use utility", "NONE", "HIGH: Tool use."),
        ("src\\utils\\tooltip.ts", "utils", "Tooltip utility", "NONE", "LOW: Tooltip."),
        ("src\\utils\\top.ts", "utils", "Top utility", "NONE", "LOW: Top."),
        ("src\\utils\\trace.ts", "utils", "Trace utility", "NONE", "LOW: Trace."),
        ("src\\utils\\tracer.ts", "utils", "Tracer utility", "NONE", "MEDIUM: Tracer."),
        ("src\\utils\\tracking.ts", "utils", "Tracking utility", "NONE", "MEDIUM: Tracking."),
        ("src\\utils\\traverse.ts", "utils", "Traverse utility", "NONE", "LOW: Traverse."),
        ("src\\utils\\tree.ts", "utils", "Tree utility", "NONE", "LOW: Tree."),
        ("src\\utils\\trim.ts", "utils", "Trim utility", "NONE", "LOW: Trim."),
        ("src\\utils\\trunc.ts", "utils", "Trunc utility", "NONE", "LOW: Trunc."),
        ("src\\utils\\truncate.ts", "utils", "Truncate utility", "NONE", "LOW: Truncate."),
        ("src\\utils\\try.ts", "utils", "Try utility", "NONE", "LOW: Try."),
        ("src\\utils\\ts.ts", "utils", "TS utility", "NONE", "LOW: TS."),
        ("src\\utils\\tsconfig.ts", "utils", "TSConfig utility", "NONE", "LOW: TSConfig."),
        ("src\\utils\\tty.ts", "utils", "TTY utility", "NONE", "LOW: TTY."),
        ("src\\utils\\tuple.ts", "utils", "Tuple utility", "NONE", "LOW: Tuple."),
        ("src\\utils\\type.ts", "utils", "Type utility", "NONE", "LOW: Type."),
        ("src\\utils\\typeCheck.ts", "utils", "Type check utility", "NONE", "LOW: Type check."),
        ("src\\utils\\typeOf.ts", "utils", "Type of utility", "NONE", "LOW: TypeOf."),
        ("src\\utils\\typedi.ts", "utils", "TypedI utility", "NONE", "MEDIUM: DI."),
        ("src\\utils\\typescript.ts", "utils", "TypeScript utility", "NONE", "LOW: TypeScript."),
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