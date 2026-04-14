"""第四十七輪分析批量更新腳本"""
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
        ("src\\utils\\startupProfiler.ts", "utils", "Startup profiler", "NONE", "MEDIUM: Startup profiler."),
        ("src\\utils\\stats.ts", "utils", "Stats utility", "NONE", "LOW: Stats."),
        ("src\\utils\\statsCache.ts", "utils", "Stats cache", "NONE", "MEDIUM: Stats cache."),
        ("src\\utils\\statusNoticeHelpers.ts", "utils", "Status notice helpers", "NONE", "LOW: Status helpers."),
        ("src\\utils\\stream.ts", "utils", "Stream utility", "NONE", "MEDIUM: Stream."),
        ("src\\utils\\streamJsonStdoutGuard.ts", "utils", "Stream JSON stdout guard", "NONE", "MEDIUM: JSON guard."),
        ("src\\utils\\streamlinedTransform.ts", "utils", "Streamlined transform", "NONE", "LOW: Transform."),
        ("src\\utils\\stringUtils.ts", "utils", "String utilities", "NONE", "LOW: String utils."),
        ("src\\utils\\systemDirectories.ts", "utils", "System directories", "NONE", "MEDIUM: Sys dirs."),
        ("src\\utils\\systemPromptType.ts", "utils", "System prompt type", "NONE", "MEDIUM: System prompt."),
        ("src\\utils\\telemetry.ts", "utils", "Telemetry utility", "NONE", "MEDIUM: Telemetry."),
        ("src\\utils\\template.ts", "utils", "Template utility", "NONE", "LOW: Template."),
        ("src\\utils\\temporaryFile.ts", "utils", "Temporary file", "NONE", "MEDIUM: Temp file."),
        ("src\\utils\\terminal.ts", "utils", "Terminal utility", "NONE", "MEDIUM: Terminal."),
        ("src\\utils\\test.ts", "utils", "Test utility", "NONE", "LOW: Test."),
        ("src\\utils\\teammate.ts", "utils", "Teammate utility", "NONE", "HIGH: Teammate."),
        ("src\\utils\\terminalHistory.ts", "utils", "Terminal history", "NONE", "MEDIUM: History."),
        ("src\\utils\\terminalTheme.ts", "utils", "Terminal theme", "NONE", "LOW: Theme."),
        ("src\\utils\\text.ts", "utils", "Text utility", "NONE", "LOW: Text."),
        ("src\\utils\\textarea.ts", "utils", "Textarea utility", "NONE", "LOW: Textarea."),
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