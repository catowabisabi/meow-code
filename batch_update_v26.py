"""第二十六輪分析批量更新腳本 - keybindings, 其餘 ink"""
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
        ("src\\keybindings\\loadUserBindings.ts", "keybindings", "Load user keybindings", "NONE", "MEDIUM: User bindings."),
        ("src\\keybindings\\match.ts", "keybindings", "Keybinding match", "NONE", "MEDIUM: Binding match."),
        ("src\\keybindings\\parser.ts", "keybindings", "Keybinding parser", "NONE", "MEDIUM: Parser."),
        ("src\\keybindings\\reservedShortcuts.ts", "keybindings", "Reserved shortcuts", "NONE", "MEDIUM: Reserved."),
        ("src\\keybindings\\resolver.ts", "keybindings", "Keybinding resolver", "NONE", "MEDIUM: Resolver."),
        ("src\\keybindings\\schema.ts", "keybindings", "Keybinding schema", "NONE", "MEDIUM: Schema."),
        ("src\\keybindings\\shortcutFormat.ts", "keybindings", "Shortcut format", "NONE", "MEDIUM: Format."),
        ("src\\keybindings\\template.ts", "keybindings", "Keybinding template", "NONE", "MEDIUM: Template."),
        ("src\\keybindings\\useKeybinding.ts", "keybindings", "Use keybinding hook", "NONE", "MEDIUM: Hook."),
        ("src\\keybindings\\useShortcutDisplay.ts", "keybindings", "Shortcut display hook", "NONE", "LOW: Display."),
        ("src\\keybindings\\index.ts", "keybindings", "Keybindings index", "NONE", "LOW: Index."),
        ("src\\keybindings\\keybindings.ts", "keybindings", "Keybindings main", "NONE", "MEDIUM: Main."),
        ("src\\keybindings\\builtinShortcuts.ts", "keybindings", "Builtin shortcuts", "NONE", "MEDIUM: Builtin."),
        ("src\\keybindings\\builtinActionBindings.ts", "keybindings", "Builtin action bindings", "NONE", "MEDIUM: Bindings."),
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