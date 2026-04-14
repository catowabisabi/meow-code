"""第二十四輪分析批量更新腳本 - ink 目錄"""
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
        ("src\\ink\\Ansi.tsx", "ink/core", "ANSI escape code handling (33365 lines)", "NONE", "MEDIUM: ANSI handling."),
        ("src\\ink\\components\\AlternateScreen.tsx", "ink/components", "Alternate screen component", "NONE", "LOW: UI component."),
        ("src\\ink\\components\\AppContext.ts", "ink/components", "App context provider", "NONE", "LOW: Context."),
        ("src\\ink\\components\\Button.tsx", "ink/components", "Button component", "NONE", "LOW: UI component."),
        ("src\\ink\\components\\ClockContext.tsx", "ink/components", "Clock context", "NONE", "LOW: Context."),
        ("src\\ink\\components\\CursorDeclarationContext.ts", "ink/components", "Cursor declaration context", "NONE", "LOW: Context."),
        ("src\\ink\\components\\ErrorOverview.tsx", "ink/components", "Error overview component", "NONE", "LOW: UI component."),
        ("src\\ink\\components\\Link.tsx", "ink/components", "Link component", "NONE", "LOW: UI component."),
        ("src\\ink\\components\\Newline.tsx", "ink/components", "Newline component", "NONE", "LOW: UI component."),
        ("src\\ink\\components\\NoSelect.tsx", "ink/components", "No select component", "NONE", "LOW: UI component."),
        ("src\\ink\\components\\RawAnsi.tsx", "ink/components", "Raw ANSI component", "NONE", "LOW: UI component."),
        ("src\\ink\\components\\ScrollBox.tsx", "ink/components", "Scroll box component", "NONE", "LOW: UI component."),
        ("src\\ink\\components\\Spacer.tsx", "ink/components", "Spacer component", "NONE", "LOW: UI component."),
        ("src\\ink\\components\\StdinContext.ts", "ink/components", "Stdin context", "NONE", "LOW: Context."),
        ("src\\ink\\components\\TerminalFocusContext.tsx", "ink/components", "Terminal focus context", "NONE", "LOW: Context."),
        ("src\\ink\\components\\TerminalSizeContext.tsx", "ink/components", "Terminal size context", "NONE", "LOW: Context."),
        ("src\\ink\\events\\emitter.ts", "ink/events", "Event emitter", "NONE", "LOW: Event system."),
        ("src\\ink\\events\\event-handlers.ts", "ink/events", "Event handlers", "NONE", "LOW: Event handlers."),
        ("src\\ink\\events\\event.ts", "ink/events", "Event types", "NONE", "LOW: Event types."),
        ("src\\ink\\events\\focus-event.ts", "ink/events", "Focus event", "NONE", "LOW: Focus event."),
        ("src\\ink\\events\\input-event.ts", "ink/events", "Input event", "NONE", "LOW: Input event."),
        ("src\\ink\\events\\keyboard-event.ts", "ink/events", "Keyboard event", "NONE", "LOW: Keyboard event."),
        ("src\\ink\\events\\terminal-event.ts", "ink/events", "Terminal event", "NONE", "LOW: Terminal event."),
        ("src\\ink\\events\\terminal-focus-event.ts", "ink/events", "Terminal focus event", "NONE", "LOW: Focus event."),
        ("src\\ink\\frame.ts", "ink/core", "Frame handling", "NONE", "LOW: Frame."),
        ("src\\ink\\get-max-width.ts", "ink/core", "Get max width utility", "NONE", "LOW: Utility."),
        ("src\\ink\\hit-test.ts", "ink/core", "Hit testing", "NONE", "LOW: Hit testing."),
        ("src\\ink\\hooks\\use-animation-frame.ts", "ink/hooks", "Animation frame hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-app.ts", "ink/hooks", "App hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-declared-cursor.ts", "ink/hooks", "Declared cursor hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-input.ts", "ink/hooks", "Input hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-interval.ts", "ink/hooks", "Interval hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-search-highlight.ts", "ink/hooks", "Search highlight hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-selection.ts", "ink/hooks", "Selection hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-stdin.ts", "ink/hooks", "Stdin hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-tab-status.ts", "ink/hooks", "Tab status hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-terminal-focus.ts", "ink/hooks", "Terminal focus hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-terminal-title.ts", "ink/hooks", "Terminal title hook", "NONE", "LOW: Hook."),
        ("src\\ink\\hooks\\use-terminal-viewport.ts", "ink/hooks", "Terminal viewport hook", "NONE", "LOW: Hook."),
        ("src\\ink\\instances.ts", "ink/core", "Ink instances", "NONE", "LOW: Instances."),
        ("src\\ink\\layout\\engine.ts", "ink/layout", "Layout engine", "NONE", "LOW: Layout engine."),
        ("src\\ink\\layout\\geometry.ts", "ink/layout", "Layout geometry", "NONE", "LOW: Geometry."),
        ("src\\ink\\layout\\node.ts", "ink/layout", "Layout node", "NONE", "LOW: Layout node."),
        ("src\\ink\\line-width-cache.ts", "ink/core", "Line width cache", "NONE", "LOW: Cache."),
        ("src\\ink\\measure-element.ts", "ink/core", "Measure element", "NONE", "LOW: Measurement."),
        ("src\\ink\\measure-text.ts", "ink/core", "Measure text", "NONE", "LOW: Measurement."),
        ("src\\ink\\node-cache.ts", "ink/core", "Node cache", "NONE", "LOW: Cache."),
        ("src\\ink\\optimizer.ts", "ink/core", "Optimizer", "NONE", "LOW: Optimizer."),
        ("src\\ink\\output.ts", "ink/core", "Output handling (26253 lines)", "NONE", "MEDIUM: Output handling."),
        ("src\\ink\\render-border.ts", "ink/render", "Render border", "NONE", "LOW: Render."),
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