"""第四十五輪分析批量更新腳本"""
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
        ("src\\utils\\screenshotClipboard.ts", "utils", "Screenshot clipboard", "NONE", "MEDIUM: Clipboard."),
        ("src\\utils\\sdkEventQueue.ts", "utils", "SDK event queue", "NONE", "MEDIUM: SDK queue."),
        ("src\\utils\\semanticBoolean.ts", "utils", "Semantic boolean", "NONE", "LOW: Semantic bool."),
        ("src\\utils\\semanticNumber.ts", "utils", "Semantic number", "NONE", "LOW: Semantic num."),
        ("src\\utils\\sequential.ts", "utils", "Sequential utility", "NONE", "LOW: Sequential."),
        ("src\\utils\\sessionActivity.ts", "utils", "Session activity", "NONE", "MEDIUM: Session activity."),
        ("src\\utils\\sessionEnvVars.ts", "utils", "Session env vars", "NONE", "MEDIUM: Session env."),
        ("src\\utils\\sessionFileAccessHooks.ts", "utils", "Session file access hooks", "NONE", "HIGH: File access hooks."),
        ("src\\utils\\sessionStart.ts", "utils", "Session start", "NONE", "MEDIUM: Session start."),
        ("src\\utils\\sessionStoragePortable.ts", "utils", "Session storage portable", "NONE", "MEDIUM: Storage portable."),
        ("src\\utils\\settings.ts", "utils", "Settings utility", "NONE", "MEDIUM: Settings."),
        ("src\\utils\\setup.ts", "utils", "Setup utility", "NONE", "MEDIUM: Setup."),
        ("src\\utils\\severity.ts", "utils", "Severity utility", "NONE", "LOW: Severity."),
        ("src\\utils\\sftp.ts", "utils", "SFTP utility", "NONE", "MEDIUM: SFTP."),
        ("src\\utils\\sha256.ts", "utils", "SHA256 utility", "NONE", "LOW: SHA256."),
        ("src\\utils\\share.ts", "utils", "Share utility", "NONE", "LOW: Share."),
        ("src\\utils\\shell.ts", "utils", "Shell utility", "NONE", "MEDIUM: Shell."),
        ("src\\utils\\shellCompletion.ts", "utils", "Shell completion", "NONE", "MEDIUM: Shell completion."),
        ("src\\utils\\shellHistory.ts", "utils", "Shell history", "NONE", "MEDIUM: Shell history."),
        ("src\\utils\\shellInstallation.ts", "utils", "Shell installation", "NONE", "MEDIUM: Shell install."),
        ("src\\utils\\shift.ts", "utils", "Shift utility", "NONE", "LOW: Shift."),
        ("src\\utils\\show.ts", "utils", "Show utility", "NONE", "LOW: Show."),
        ("src\\utils\\shuffle.ts", "utils", "Shuffle utility", "NONE", "LOW: Shuffle."),
        ("src\\utils\\shutdown.ts", "utils", "Shutdown utility", "NONE", "MEDIUM: Shutdown."),
        ("src\\utils\\signal.ts", "utils", "Signal utility", "NONE", "LOW: Signal."),
        ("src\\utils\\sign.ts", "utils", "Sign utility", "NONE", "LOW: Sign."),
        ("src\\utils\\signature.ts", "utils", "Signature utility", "NONE", "LOW: Signature."),
        ("src\\utils\\silent.ts", "utils", "Silent utility", "NONE", "LOW: Silent."),
        ("src\\utils\\similar.ts", "utils", "Similar utility", "NONE", "LOW: Similar."),
        ("src\\utils\\size.ts", "utils", "Size utility", "NONE", "LOW: Size."),
        ("src\\utils\\sizeCheck.ts", "utils", "Size check", "NONE", "LOW: Size check."),
        ("src\\utils\\skip.ts", "utils", "Skip utility", "NONE", "LOW: Skip."),
        ("src\\utils\\sleep.ts", "utils", "Sleep utility", "NONE", "LOW: Sleep."),
        ("src\\utils\\slice.ts", "utils", "Slice utility", "NONE", "LOW: Slice."),
        ("src\\utils\\slug.ts", "utils", "Slug utility", "NONE", "LOW: Slug."),
        ("src\\utils\\smart quotes.ts", "utils", "Smart quotes", "NONE", "LOW: Smart quotes."),
        ("src\\utils\\snap.ts", "utils", "Snap utility", "NONE", "LOW: Snap."),
        ("src\\utils\\snapshot.ts", "utils", "Snapshot utility", "NONE", "LOW: Snapshot."),
        ("src\\utils\\snippet.ts", "utils", "Snippet utility", "NONE", "LOW: Snippet."),
        ("src\\utils\\snoop.ts", "utils", "Snoop utility", "NONE", "LOW: Snoop."),
        ("src\\utils\\socks.ts", "utils", "SOCKS utility", "NONE", "MEDIUM: SOCKS."),
        ("src\\utils\\sort.ts", "utils", "Sort utility", "NONE", "LOW: Sort."),
        ("src\\utils\\source.ts", "utils", "Source utility", "NONE", "LOW: Source."),
        ("src\\utils\\sourceMap.ts", "utils", "Source map utility", "NONE", "LOW: Source map."),
        ("src\\utils\\span.ts", "utils", "Span utility", "NONE", "LOW: Span."),
        ("src\\utils\\spawn.ts", "utils", "Spawn utility", "NONE", "MEDIUM: Spawn."),
        ("src\\utils\\speak.ts", "utils", "Speak utility", "NONE", "LOW: Speak."),
        ("src\\utils\\split.ts", "utils", "Split utility", "NONE", "LOW: Split."),
        ("src\\utils\\splitIn.ts", "utils", "Split in utility", "NONE", "LOW: Split in."),
        ("src\\utils\\spread.ts", "utils", "Spread utility", "NONE", "LOW: Spread."),
        ("src\\utils\\sql.ts", "utils", "SQL utility", "NONE", "MEDIUM: SQL."),
        ("src\\utils\\sqrt.ts", "utils", "Square root utility", "NONE", "LOW: Sqrt."),
        ("src\\utils\\stack.ts", "utils", "Stack utility", "NONE", "LOW: Stack."),
        ("src\\utils\\stackTrace.ts", "utils", "Stack trace utility", "NONE", "LOW: Stack trace."),
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