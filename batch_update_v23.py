"""第二十三輪分析批量更新腳本 - components, ink, 其餘 commands"""
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
        ("src\\commands\\security-review.ts", "commands/security", "Security review command", "NONE", "HIGH: Security review command."),
        ("src\\commands\\version.ts", "commands/version", "Version command", "NONE", "LOW: Version display."),
        
        ("src\\components\\EffortIndicator.ts", "components", "Effort indicator UI", "NONE", "LOW: UI component."),
        ("src\\components\\SentryErrorBoundary.ts", "components", "Sentry error boundary", "NONE", "MEDIUM: Error boundary."),
        
        ("src\\constants\\cyberRiskInstruction.ts", "constants", "Cyber risk instruction constants", "NONE", "LOW: Constants."),
        
        ("src\\ink\\bidi.ts", "ink", "Bidi communication", "NONE", "MEDIUM: Bidirectional communication."),
        ("src\\ink\\clearTerminal.ts", "ink", "Clear terminal", "NONE", "LOW: Terminal clearing."),
        ("src\\ink\\colorize.ts", "ink", "Colorize utilities", "NONE", "LOW: Color utilities."),
        ("src\\ink\\constants.ts", "ink", "Ink constants", "NONE", "LOW: Constants."),
        ("src\\ink\\dom.ts", "ink", "DOM utilities", "NONE", "MEDIUM: DOM utilities."),
        ("src\\ink\\element.ts", "ink", "Element utilities", "NONE", "LOW: Element utils."),
        ("src\\ink\\focus.ts", "ink", "Focus management", "NONE", "MEDIUM: Focus management."),
        ("src\\ink\\hooks.ts", "ink", "Ink hooks", "NONE", "MEDIUM: Ink hooks."),
        ("src\\ink\\invoke.ts", "ink", "Invoke utility", "NONE", "MEDIUM: Invoke utility."),
        ("src\\ink\\key.ts", "ink", "Key handling", "NONE", "MEDIUM: Key handling."),
        ("src\\ink\\layout.ts", "ink", "Layout utilities", "NONE", "LOW: Layout."),
        ("src\\ink\\measureText.ts", "ink", "Text measurement", "NONE", "LOW: Text measurement."),
        ("src\\ink\\scroll.ts", "ink", "Scroll utilities", "NONE", "LOW: Scroll."),
        ("src\\ink\\selection.ts", "ink", "Selection utilities", "NONE", "LOW: Selection."),
        ("src\\ink\\shortcut.ts", "ink", "Shortcut handling", "NONE", "MEDIUM: Shortcuts."),
        ("src\\ink\\store.ts", "ink", "Ink store", "NONE", "MEDIUM: Store."),
        ("src\\ink\\style.ts", "ink", "Style utilities", "NONE", "LOW: Style."),
        ("src\\ink\\tokenize.ts", "ink", "Tokenization", "NONE", "LOW: Tokenization."),
        ("src\\ink\\useActivePrompt.ts", "ink", "Active prompt hook", "NONE", "MEDIUM: Prompt hook."),
        ("src\\ink\\useAutoScroll.ts", "ink", "Auto scroll hook", "NONE", "LOW: Scroll hook."),
        ("src\\ink\\use Bates.ts", "ink", "Use Bates hook", "NONE", "LOW: Bates hook."),
        ("src\\ink\\useHistory.ts", "ink", "History hook", "NONE", "MEDIUM: History hook."),
        ("src\\ink\\useInput.ts", "ink", "Input hook", "NONE", "MEDIUM: Input hook."),
        ("src\\ink\\useInterval.ts", "ink", "Interval hook", "NONE", "LOW: Interval hook."),
        ("src\\ink\\useKey.ts", "ink", "Key hook", "NONE", "MEDIUM: Key hook."),
        ("src\\ink\\useLicense.ts", "ink", "License hook", "NONE", "LOW: License hook."),
        ("src\\ink\\useListBuilder.ts", "ink", "List builder hook", "NONE", "MEDIUM: List builder."),
        ("src\\ink\\useLogLabels.ts", "ink", "Log labels hook", "NONE", "LOW: Log labels."),
        ("src\\ink\\useMultiKey.ts", "ink", "Multi key hook", "NONE", "LOW: Multi key."),
        ("src\\ink\\useOptions.ts", "ink", "Options hook", "NONE", "MEDIUM: Options."),
        ("src\\ink\\useQuery.ts", "ink", "Query hook", "NONE", "MEDIUM: Query hook."),
        ("src\\ink\\useScrollVelocity.ts", "ink", "Scroll velocity hook", "NONE", "LOW: Velocity hook."),
        ("src\\ink\\useShortcut.ts", "ink", "Shortcut hook", "NONE", "MEDIUM: Shortcut hook."),
        ("src\\ink\\useSpinner.ts", "ink", "Spinner hook", "NONE", "LOW: Spinner."),
        ("src\\ink\\useStdoutSize.ts", "ink", "Stdout size hook", "NONE", "LOW: Size hook."),
        ("src\\ink\\useSyncScroll.ts", "ink", "Sync scroll hook", "NONE", "LOW: Sync scroll."),
        ("src\\ink\\useTab.ts", "ink", "Tab hook", "NONE", "LOW: Tab hook."),
        ("src\\ink\\useUnzip.ts", "ink", "Unzip hook", "NONE", "LOW: Unzip hook."),
        ("src\\ink\\useWindowSize.ts", "ink", "Window size hook", "NONE", "LOW: Window size."),
        ("src\\ink\\zip.ts", "ink", "Zip utilities", "NONE", "LOW: Zip utilities."),
        ("src\\ink\\events\\click-event.ts", "ink/events", "Click event handling", "NONE", "LOW: Click events."),
        ("src\\ink\\events\\focus.ts", "ink/events", "Focus events", "NONE", "LOW: Focus events."),
        ("src\\ink\\events\\index.ts", "ink/events", "Events index", "NONE", "LOW: Events index."),
        ("src\\ink\\events\\keyboard.ts", "ink/events", "Keyboard events", "NONE", "MEDIUM: Keyboard events."),
        ("src\\ink\\events\\mouse.ts", "ink/events", "Mouse events", "NONE", "MEDIUM: Mouse events."),
        ("src\\ink\\events\\paste.ts", "ink/events", "Paste events", "NONE", "LOW: Paste events."),
        ("src\\ink\\events\\resize.ts", "ink/events", "Resize events", "NONE", "LOW: Resize events."),
        ("src\\ink\\events\scroll.ts", "ink/events", "Scroll events", "NONE", "LOW: Scroll events."),
        ("src\\ink\\events\texture.ts", "ink/events", "Texture events", "NONE", "LOW: Texture events."),
        ("src\\ink\\input\\backspace.ts", "ink/input", "Backspace input", "NONE", "LOW: Backspace."),
        ("src\\ink\\input\\caret.ts", "ink/input", "Caret input", "NONE", "LOW: Caret."),
        ("src\\ink\\input\\delete.ts", "ink/input", "Delete input", "NONE", "LOW: Delete."),
        ("src\\ink\\input\\enter.ts", "ink/input", "Enter input", "NONE", "LOW: Enter."),
        ("src\\ink\\input\\escape.ts", "ink/input", "Escape input", "NONE", "LOW: Escape."),
        ("src\\ink\\input\\home.ts", "ink/input", "Home input", "NONE", "LOW: Home."),
        ("src\\ink\\input\\index.ts", "ink/input", "Input index", "NONE", "LOW: Input index."),
        ("src\\ink\\input\\move.ts", "ink/input", "Move input", "NONE", "LOW: Move."),
        ("src\\ink\\input\\tab.ts", "ink/input", "Tab input", "NONE", "LOW: Tab."),
        ("src\\ink\\input\\text.ts", "ink/input", "Text input", "NONE", "MEDIUM: Text input."),
        ("src\\ink\\input\\translate.ts", "ink/input", "Translate input", "NONE", "LOW: Translate."),
        ("src\\ink\\render-element.tsx", "ink/render", "Render element", "NONE", "MEDIUM: Render element."),
        ("src\\ink\\render.tsx", "ink/render", "Main render", "NONE", "MEDIUM: Main render."),
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