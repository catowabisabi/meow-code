"""第三十九輪分析批量更新腳本"""
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
        ("src\\utils\\heatmap.ts", "utils", "Heatmap utility", "NONE", "LOW: Heatmap."),
        ("src\\utils\\hooks.ts", "utils", "Hooks utility", "NONE", "MEDIUM: Hooks."),
        ("src\\utils\\horizontalScroll.ts", "utils", "Horizontal scroll", "NONE", "LOW: Scroll."),
        ("src\\utils\\hyperlink.ts", "utils", "Hyperlink utility", "NONE", "LOW: Hyperlink."),
        ("src\\utils\\idleTimeout.ts", "utils", "Idle timeout", "NONE", "MEDIUM: Timeout."),
        ("src\\utils\\imagePaste.ts", "utils", "Image paste", "NONE", "MEDIUM: Image paste."),
        ("src\\utils\\imageResizer.ts", "utils", "Image resizer", "NONE", "MEDIUM: Image resize."),
        ("src\\utils\\imageStore.ts", "utils", "Image store", "NONE", "MEDIUM: Image store."),
        ("src\\utils\\imageValidation.ts", "utils", "Image validation", "NONE", "MEDIUM: Image validation."),
        ("src\\utils\\immediateCommand.ts", "utils", "Immediate command", "NONE", "MEDIUM: Immediate command."),
        ("src\\utils\\immutable.ts", "utils", "Immutable utility", "NONE", "LOW: Immutable."),
        ("src\\utils\\implies.ts", "utils", "Implies utility", "NONE", "LOW: Implies."),
        ("src\\utils\\inCato.ts", "utils", "In Cato check", "NONE", "LOW: Cato check."),
        ("src\\utils\\inDirectory.ts", "utils", "In directory check", "NONE", "LOW: Directory check."),
        ("src\\utils\\index.ts", "utils", "Index utility", "NONE", "LOW: Index."),
        ("src\\utils\\init.ts", "utils", "Init utility", "NONE", "LOW: Init."),
        ("src\\utils\\initial.ts", "utils", "Initial utility", "NONE", "LOW: Initial."),
        ("src\\utils\\inline.ts", "utils", "Inline utility", "NONE", "LOW: Inline."),
        ("src\\utils\\input.ts", "utils", "Input utility", "NONE", "LOW: Input."),
        ("src\\utils\\inputPrompt.ts", "utils", "Input prompt", "NONE", "LOW: Input prompt."),
        ("src\\utils\\insert.ts", "utils", "Insert utility", "NONE", "LOW: Insert."),
        ("src\\utils\\inspect.ts", "utils", "Inspect utility", "NONE", "LOW: Inspect."),
        ("src\\utils\\instance.ts", "utils", "Instance utility", "NONE", "LOW: Instance."),
        ("src\\utils\\int.ts", "utils", "Int utility", "NONE", "LOW: Int."),
        ("src\\utils\\integer.ts", "utils", "Integer utility", "NONE", "LOW: Integer."),
        ("src\\utils\\interact.ts", "utils", "Interact utility", "NONE", "MEDIUM: Interact."),
        ("src\\utils\\interface.ts", "utils", "Interface utility", "NONE", "LOW: Interface."),
        ("src\\utils\\interval.ts", "utils", "Interval utility", "NONE", "LOW: Interval."),
        ("src\\utils\\interpolate.ts", "utils", "Interpolate utility", "NONE", "LOW: Interpolate."),
        ("src\\utils\\intersect.ts", "utils", "Intersect utility", "NONE", "LOW: Intersect."),
        ("src\\utils\\intersection.ts", "utils", "Intersection utility", "NONE", "LOW: Intersection."),
        ("src\\utils\\intervalMap.ts", "utils", "Interval map", "NONE", "LOW: Interval map."),
        ("src\\utils\\into.ts", "utils", "Into utility", "NONE", "LOW: Into."),
        ("src\\utils\\invalid.ts", "utils", "Invalid utility", "NONE", "LOW: Invalid."),
        ("src\\utils\\invoke.ts", "utils", "Invoke utility", "NONE", "LOW: Invoke."),
        ("src\\utils\\invokeFunction.ts", "utils", "Invoke function", "NONE", "LOW: Invoke function."),
        ("src\\utils\\io.ts", "utils", "IO utility", "NONE", "MEDIUM: IO."),
        ("src\\utils\\ip.ts", "utils", "IP utility", "NONE", "LOW: IP."),
        ("src\\utils\\is.ts", "utils", "Is utility", "NONE", "LOW: Is."),
        ("src\\utils\\isAppleTerminal.ts", "utils", "Is Apple Terminal", "NONE", "LOW: Apple Terminal."),
        ("src\\utils\\isCI.ts", "utils", "Is CI check", "NONE", "LOW: CI check."),
        ("src\\utils\\isDesktop.ts", "utils", "Is desktop check", "NONE", "LOW: Desktop check."),
        ("src\\utils\\isLinux.ts", "utils", "Is Linux check", "NONE", "LOW: Linux check."),
        ("src\\utils\\isMac.ts", "utils", "Is Mac check", "NONE", "LOW: Mac check."),
        ("src\\utils\\isMailto.ts", "utils", "Is mailto check", "NONE", "LOW: Mailto check."),
        ("src\\utils\\isMobile.ts", "utils", "Is mobile check", "NONE", "LOW: Mobile check."),
        ("src\\utils\\isomorphic.ts", "utils", "Isomorphic utility", "NONE", "LOW: Isomorphic."),
        ("src\\utils\\isPortable.ts", "utils", "Is portable check", "NONE", "LOW: Portable check."),
        ("src\\utils\\isPWA.ts", "utils", "Is PWA check", "NONE", "LOW: PWA check."),
        ("src\\utils\\isRemote.ts", "utils", "Is remote check", "NONE", "MEDIUM: Remote check."),
        ("src\\utils\\isWindows.ts", "utils", "Is Windows check", "NONE", "LOW: Windows check."),
        ("src\\utils\\iterate.ts", "utils", "Iterate utility", "NONE", "LOW: Iterate."),
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