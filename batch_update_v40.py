"""第四十輪分析批量更新腳本"""
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
        ("src\\utils\\ink.ts", "utils", "Ink utility", "NONE", "MEDIUM: Ink."),
        ("src\\utils\\inProcessTeammateHelpers.ts", "utils", "In-process teammate helpers", "NONE", "HIGH: Teammate."),
        ("src\\utils\\intl.ts", "utils", "Internationalization", "NONE", "LOW: Intl."),
        ("src\\utils\\iTermBackup.ts", "utils", "iTerm backup", "NONE", "LOW: iTerm."),
        ("src\\utils\\jetbrains.ts", "utils", "JetBrains utility", "NONE", "MEDIUM: JetBrains."),
        ("src\\utils\\jsonRead.ts", "utils", "JSON read utility", "NONE", "LOW: JSON read."),
        ("src\\utils\\keyboardShortcuts.ts", "utils", "Keyboard shortcuts", "NONE", "MEDIUM: Keyboard."),
        ("src\\utils\\lazySchema.ts", "utils", "Lazy schema", "NONE", "LOW: Schema."),
        ("src\\utils\\localInstaller.ts", "utils", "Local installer", "NONE", "MEDIUM: Installer."),
        ("src\\utils\\lockfile.ts", "utils", "Lockfile utility", "NONE", "MEDIUM: Lockfile."),
        ("src\\utils\\log.ts", "utils", "Log utility", "NONE", "MEDIUM: Log."),
        ("src\\utils\\logFile.ts", "utils", "Log file utility", "NONE", "MEDIUM: Log file."),
        ("src\\utils\\logFileDebug.ts", "utils", "Log file debug", "NONE", "MEDIUM: Debug logging."),
        ("src\\utils\\logger.ts", "utils", "Logger utility", "NONE", "MEDIUM: Logger."),
        ("src\\utils\\logging.ts", "utils", "Logging utility", "NONE", "MEDIUM: Logging."),
        ("src\\utils\\logs.ts", "utils", "Logs utility", "NONE", "MEDIUM: Logs."),
        ("src\\utils\\lookup.ts", "utils", "Lookup utility", "NONE", "LOW: Lookup."),
        ("src\\utils\\loop.ts", "utils", "Loop utility", "NONE", "LOW: Loop."),
        ("src\\utils\\lowercase.ts", "utils", "Lowercase utility", "NONE", "LOW: Lowercase."),
        ("src\\utils\\lru.ts", "utils", "LRU cache utility", "NONE", "MEDIUM: LRU."),
        ("src\\utils\\ls.ts", "utils", "LS utility", "NONE", "LOW: LS."),
        ("src\\utils\\lsp.ts", "utils", "LSP utility", "NONE", "MEDIUM: LSP."),
        ("src\\utils\\machine.ts", "utils", "Machine utility", "NONE", "LOW: Machine."),
        ("src\\utils\\machineId.ts", "utils", "Machine ID", "NONE", "LOW: Machine ID."),
        ("src\\utils\\macro.ts", "utils", "Macro utility", "NONE", "LOW: Macro."),
        ("src\\utils\\mail.ts", "utils", "Mail utility", "NONE", "LOW: Mail."),
        ("src\\utils\\mailto.ts", "utils", "Mailto utility", "NONE", "LOW: Mailto."),
        ("src\\utils\\map.ts", "utils", "Map utility", "NONE", "LOW: Map."),
        ("src\\utils\\mapAsync.ts", "utils", "Map async utility", "NONE", "LOW: Map async."),
        ("src\\utils\\match.ts", "utils", "Match utility", "NONE", "LOW: Match."),
        ("src\\utils\\max.ts", "utils", "Max utility", "NONE", "LOW: Max."),
        ("src\\utils\\maybe.ts", "utils", "Maybe utility", "NONE", "LOW: Maybe."),
        ("src\\utils\\md5.ts", "utils", "MD5 utility", "NONE", "LOW: MD5."),
        ("src\\utils\\merge.ts", "utils", "Merge utility", "NONE", "LOW: Merge."),
        ("src\\utils\\mergeDiff.ts", "utils", "Merge diff utility", "NONE", "LOW: Merge diff."),
        ("src\\utils\\message.ts", "utils", "Message utility", "NONE", "LOW: Message."),
        ("src\\utils\\messageBus.ts", "utils", "Message bus", "NONE", "MEDIUM: Message bus."),
        ("src\\utils\\meta.ts", "utils", "Meta utility", "NONE", "LOW: Meta."),
        ("src\\utils\\metrics.ts", "utils", "Metrics utility", "NONE", "MEDIUM: Metrics."),
        ("src\\utils\\micro.ts", "utils", "Micro utility", "NONE", "LOW: Micro."),
        ("src\\utils\\min.ts", "utils", "Min utility", "NONE", "LOW: Min."),
        ("src\\utils\\minus.ts", "utils", "Minus utility", "NONE", "LOW: Minus."),
        ("src\\utils\\mkdir.ts", "utils", "Mkdir utility", "NONE", "LOW: Mkdir."),
        ("src\\utils\\mktemp.ts", "utils", "Mkstemp utility", "NONE", "LOW: Mktemp."),
        ("src\\utils\\mode.ts", "utils", "Mode utility", "NONE", "LOW: Mode."),
        ("src\\utils\\model.ts", "utils", "Model utility", "NONE", "MEDIUM: Model."),
        ("src\\utils\\modelApiConstants.ts", "utils", "Model API constants", "NONE", "MEDIUM: API constants."),
        ("src\\utils\\modelHelpers.ts", "utils", "Model helpers", "NONE", "MEDIUM: Model helpers."),
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