"""第二十五輪分析批量更新腳本 - ink 其餘檔案, termio"""
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
        ("src\\ink\\render-node-to-output.ts", "ink/render", "Render node to output (63392 lines)", "NONE", "MEDIUM: Core rendering."),
        ("src\\ink\\render-to-screen.ts", "ink/render", "Render to screen", "NONE", "MEDIUM: Screen rendering."),
        ("src\\ink\\root.ts", "ink/core", "Root component", "NONE", "LOW: Root."),
        ("src\\ink\\searchHighlight.ts", "ink/core", "Search highlight", "NONE", "LOW: Search."),
        ("src\\ink\\squash-text-nodes.ts", "ink/core", "Squash text nodes", "NONE", "LOW: Optimization."),
        ("src\\ink\\stringWidth.ts", "ink/core", "String width calculation", "NONE", "LOW: Width calc."),
        ("src\\ink\\supports-hyperlinks.ts", "ink/core", "Hyperlink support detection", "NONE", "LOW: Hyperlinks."),
        ("src\\ink\\tabstops.ts", "ink/core", "Tabstop handling", "NONE", "LOW: Tabs."),
        ("src\\ink\\termio.ts", "ink/termio", "Termio utilities", "NONE", "LOW: Termio."),
        ("src\\ink\\useTerminalNotification.ts", "ink/hooks", "Terminal notification hook", "NONE", "LOW: Notification."),
        ("src\\ink\\warn.ts", "ink/core", "Warning utility", "NONE", "LOW: Warning."),
        ("src\\ink\\widest-line.ts", "ink/core", "Widest line utility", "NONE", "LOW: Width utility."),
        ("src\\ink\\wrap-text.ts", "ink/core", "Text wrapping", "NONE", "LOW: Text wrap."),
        ("src\\ink\\wrapAnsi.ts", "ink/core", "ANSI wrapping", "NONE", "LOW: Wrap ANSI."),
        ("src\\ink\\ink.tsx", "ink/core", "Main ink entry (252019 lines)", "NONE", "HIGH: Core ink engine - massive file."),
        ("src\\ink\\log-update.ts", "ink/core", "Log update handling (27284 lines)", "NONE", "MEDIUM: Log updates."),
        ("src\\ink\\screen.ts", "ink/core", "Screen handling (49390 lines)", "NONE", "MEDIUM: Screen handling."),
        ("src\\ink\\output.ts", "ink/core", "Output handling (26253 lines)", "NONE", "MEDIUM: Output."),
        ("src\\ink\\reconciler.ts", "ink/core", "Reconciler (14718 lines)", "NONE", "MEDIUM: Reconciler."),
        ("src\\ink\\parse-keypress.ts", "ink/core", "Keypress parsing (23458 lines)", "NONE", "MEDIUM: Keypress parsing."),
        ("src\\ink\\selection.ts", "ink/core", "Selection handling (34933 lines)", "NONE", "MEDIUM: Selection."),
        ("src\\ink\\styles.ts", "ink/core", "Styles handling (21006 lines)", "NONE", "MEDIUM: Styles."),
        ("src\\ink\\terminal.ts", "ink/core", "Terminal handling (8302 lines)", "NONE", "MEDIUM: Terminal."),
        ("src\\ink\\terminal-querier.ts", "ink/core", "Terminal querier (7843 lines)", "NONE", "MEDIUM: Terminal query."),
        ("src\\ink\\colorize.ts", "ink/core", "Colorize (7875 lines)", "NONE", "LOW: Color."),
        ("src\\ink\\dom.ts", "ink/core", "DOM utilities (15252 lines)", "NONE", "MEDIUM: DOM."),
        ("src\\ink\\clearTerminal.ts", "ink/core", "Clear terminal (2087 lines)", "NONE", "LOW: Clear."),
        ("src\\ink\\focus.ts", "ink/core", "Focus management (5222 lines)", "NONE", "MEDIUM: Focus."),
        ("src\\ink\\bidi.ts", "ink/core", "Bidi support (4290 lines)", "NONE", "LOW: Bidi."),
        ("src\\ink\\constants.ts", "ink/core", "Constants (199 lines)", "NONE", "LOW: Constants."),
        ("src\\ink\\render-border.ts", "ink/render", "Border rendering (6739 lines)", "NONE", "LOW: Border."),
        ("src\\ink\\renderer.ts", "ink/render", "Renderer (7749 lines)", "NONE", "MEDIUM: Renderer."),
        ("src\\ink\\render-to-screen.ts", "ink/render", "Screen rendering (8669 lines)", "NONE", "MEDIUM: Screen."),
        ("src\\ink\\terminal-focus-state.ts", "ink/core", "Terminal focus state (1217 lines)", "NONE", "LOW: Focus state."),
        ("src\\ink\\suppports-hyperlinks.ts", "ink/core", "Hyperlink support (1712 lines)", "NONE", "LOW: Hyperlinks."),
        ("src\\ink\\terminal.ts", "ink/core", "Terminal (8302 lines)", "NONE", "MEDIUM: Terminal."),
        ("src\\ink\\termio\\termio.ts", "ink/termio", "Termio main", "NONE", "LOW: Termio."),
        ("src\\ink\\termio\\input.ts", "ink/termio", "Termio input", "NONE", "LOW: Input."),
        ("src\\ink\\termio\\output.ts", "ink/termio", "Termio output", "NONE", "LOW: Output."),
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