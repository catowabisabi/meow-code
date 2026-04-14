"""第五十八輪分析批量更新腳本"""
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
        ("src\\utils\\powershell\\dangerousCmdlets.ts", "utils/powershell", "Dangerous PowerShell cmdlets", "NONE", "HIGH: Dangerous cmdlets."),
        ("src\\utils\\powershell\\parser.ts", "utils/powershell", "PowerShell parser", "NONE", "MEDIUM: Parser."),
        ("src\\utils\\powershell\\staticPrefix.ts", "utils/powershell", "PowerShell static prefix", "NONE", "LOW: Static prefix."),
        ("src\\utils\\processUserInput\\processTextPrompt.ts", "utils/input", "Process text prompt", "NONE", "MEDIUM: Text prompt."),
        ("src\\utils\\processUserInput\\processUserInput.ts", "utils/input", "Process user input", "NONE", "MEDIUM: User input."),
        ("src\\utils\\secureStorage\\fallbackStorage.ts", "utils/storage", "Fallback storage", "NONE", "HIGH: Fallback storage."),
        ("src\\utils\\secureStorage\\index.ts", "utils/storage", "Secure storage index", "NONE", "HIGH: Storage index."),
        ("src\\utils\\secureStorage\\keychainPrefetch.ts", "utils/storage", "Keychain prefetch", "NONE", "HIGH: Keychain."),
        ("src\\utils\\secureStorage\\macOsKeychainHelpers.ts", "utils/storage", "macOS keychain helpers", "NONE", "HIGH: Keychain helpers."),
        ("src\\utils\\secureStorage\\macOsKeychainStorage.ts", "utils/storage", "macOS keychain storage", "NONE", "HIGH: Keychain storage."),
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