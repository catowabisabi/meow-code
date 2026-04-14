"""第四十四輪分析批量更新腳本"""
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
        ("src\\utils\\QueryGuard.ts", "utils", "Query guard", "NONE", "HIGH: Query guard."),
        ("src\\utils\\queryHelpers.ts", "utils", "Query helpers", "NONE", "MEDIUM: Query helpers."),
        ("src\\utils\\queryProfiler.ts", "utils", "Query profiler", "NONE", "MEDIUM: Query profiler."),
        ("src\\utils\\queueProcessor.ts", "utils", "Queue processor", "NONE", "MEDIUM: Queue processor."),
        ("src\\utils\\readEditContext.ts", "utils", "Read edit context", "NONE", "MEDIUM: Edit context."),
        ("src\\utils\\readFileInRange.ts", "utils", "Read file in range", "NONE", "LOW: File range."),
        ("src\\utils\\releaseNotes.ts", "utils", "Release notes", "NONE", "LOW: Release notes."),
        ("src\\utils\\renderOptions.ts", "utils", "Render options", "NONE", "LOW: Render options."),
        ("src\\utils\\ripgrep.ts", "utils", "Ripgrep wrapper", "NONE", "MEDIUM: Ripgrep."),
        ("src\\utils\\sanitization.ts", "utils", "Sanitization utility", "NONE", "MEDIUM: Sanitization."),
        ("src\\utils\\save.ts", "utils", "Save utility", "NONE", "LOW: Save."),
        ("src\\utils\\scaffold.ts", "utils", "Scaffold utility", "NONE", "LOW: Scaffold."),
        ("src\\utils\\scale.ts", "utils", "Scale utility", "NONE", "LOW: Scale."),
        ("src\\utils\\scan.ts", "utils", "Scan utility", "NONE", "LOW: Scan."),
        ("src\\utils\\scatter.ts", "utils", "Scatter utility", "NONE", "LOW: Scatter."),
        ("src\\utils\\schema.ts", "utils", "Schema utility", "NONE", "LOW: Schema."),
        ("src\\utils\\scope.ts", "utils", "Scope utility", "NONE", "LOW: Scope."),
        ("src\\utils\\screen.ts", "utils", "Screen utility", "NONE", "LOW: Screen."),
        ("src\\utils\\screenRecordingWarning.ts", "utils", "Screen recording warning", "NONE", "MEDIUM: Warning."),
        ("src\\utils\\screenshot.ts", "utils", "Screenshot utility", "NONE", "MEDIUM: Screenshot."),
        ("src\\utils\\search.ts", "utils", "Search utility", "NONE", "LOW: Search."),
        ("src\\utils\\searchIndex.ts", "utils", "Search index", "NONE", "MEDIUM: Search index."),
        ("src\\utils\\seconds.ts", "utils", "Seconds utility", "NONE", "LOW: Seconds."),
        ("src\\utils\\secret.ts", "utils", "Secret utility", "NONE", "MEDIUM: Secret."),
        ("src\\utils\\section.ts", "utils", "Section utility", "NONE", "LOW: Section."),
        ("src\\utils\\secure.ts", "utils", "Secure utility", "NONE", "MEDIUM: Secure."),
        ("src\\utils\\secureOpen.ts", "utils", "Secure open", "NONE", "MEDIUM: Secure open."),
        ("src\\utils\\seed.ts", "utils", "Seed utility", "NONE", "LOW: Seed."),
        ("src\\utils\\select.ts", "utils", "Select utility", "NONE", "LOW: Select."),
        ("src\\utils\\semaphore.ts", "utils", "Semaphore utility", "NONE", "LOW: Semaphore."),
        ("src\\utils\\semver.ts", "utils", "Semver utility", "NONE", "LOW: Semver."),
        ("src\\utils\\send.ts", "utils", "Send utility", "NONE", "LOW: Send."),
        ("src\\utils\\sentinel.ts", "utils", "Sentinel utility", "NONE", "LOW: Sentinel."),
        ("src\\utils\\sequence.ts", "utils", "Sequence utility", "NONE", "LOW: Sequence."),
        ("src\\utils\\serialization.ts", "utils", "Serialization utility", "NONE", "LOW: Serialization."),
        ("src\\utils\\serialize.ts", "utils", "Serialize utility", "NONE", "LOW: Serialize."),
        ("src\\utils\\server.ts", "utils", "Server utility", "NONE", "MEDIUM: Server."),
        ("src\\utils\\session.ts", "utils", "Session utility", "NONE", "MEDIUM: Session."),
        ("src\\utils\\sessionId.ts", "utils", "Session ID utility", "NONE", "LOW: Session ID."),
        ("src\\utils\\set.ts", "utils", "Set utility", "NONE", "LOW: Set."),
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