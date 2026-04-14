"""第三十六輪分析批量更新腳本"""
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
        ("src\\utils\\execFileNoThrow.ts", "utils", "Exec file no throw", "NONE", "MEDIUM: Exec."),
        ("src\\utils\\execFileNoThrowPortable.ts", "utils", "Exec file portable", "NONE", "MEDIUM: Exec portable."),
        ("src\\utils\\execSyncWrapper.ts", "utils", "Exec sync wrapper", "NONE", "MEDIUM: Exec wrapper."),
        ("src\\utils\\extraUsage.ts", "utils", "Extra usage tracking", "NONE", "MEDIUM: Usage tracking."),
        ("src\\utils\\fastMode.ts", "utils", "Fast mode utility", "NONE", "MEDIUM: Fast mode."),
        ("src\\utils\\fileHistory.ts", "utils", "File history", "NONE", "MEDIUM: History."),
        ("src\\utils\\fileOperationAnalytics.ts", "utils", "File operation analytics", "NONE", "MEDIUM: Analytics."),
        ("src\\utils\\fileRead.ts", "utils", "File read utility", "NONE", "LOW: File read."),
        ("src\\utils\\fileReadCache.ts", "utils", "File read cache", "NONE", "MEDIUM: Cache."),
        ("src\\utils\\fileStateCache.ts", "utils", "File state cache", "NONE", "MEDIUM: State cache."),
        ("src\\utils\\fileTransfer.ts", "utils", "File transfer", "NONE", "MEDIUM: Transfer."),
        ("src\\utils\\fileWrite.ts", "utils", "File write utility", "NONE", "LOW: File write."),
        ("src\\utils\\filename.ts", "utils", "Filename utility", "NONE", "LOW: Filename."),
        ("src\\utils\\files.ts", "utils", "Files utility", "NONE", "MEDIUM: Files."),
        ("src\\utils\\filesystem.ts", "utils", "Filesystem utility", "NONE", "MEDIUM: Filesystem."),
        ("src\\utils\\filter.ts", "utils", "Filter utility", "NONE", "LOW: Filter."),
        ("src\\utils\\find.ts", "utils", "Find utility", "NONE", "LOW: Find."),
        ("src\\utils\\findAll.ts", "utils", "Find all utility", "NONE", "LOW: Find all."),
        ("src\\utils\\findUp.ts", "utils", "Find up utility", "NONE", "LOW: Find up."),
        ("src\\utils\\first.ts", "utils", "First utility", "NONE", "LOW: First."),
        ("src\\utils\\flat.ts", "utils", "Flat utility", "NONE", "LOW: Flat."),
        ("src\\utils\\flatMap.ts", "utils", "Flat map utility", "NONE", "LOW: Flat map."),
        ("src\\utils\\flatten.ts", "utils", "Flatten utility", "NONE", "LOW: Flatten."),
        ("src\\utils\\flex.ts", "utils", "Flex utility", "NONE", "LOW: Flex."),
        ("src\\utils\\flip.ts", "utils", "Flip utility", "NONE", "LOW: Flip."),
        ("src\\utils\\float.ts", "utils", "Float utility", "NONE", "LOW: Float."),
        ("src\\utils\\floor.ts", "utils", "Floor utility", "NONE", "LOW: Floor."),
        ("src\\utils\\flow.ts", "utils", "Flow utility", "NONE", "LOW: Flow."),
        ("src\\utils\\flush.ts", "utils", "Flush utility", "NONE", "LOW: Flush."),
        ("src\\utils\\fn.ts", "utils", "Function utility", "NONE", "LOW: Fn."),
        ("src\\utils\\fold.ts", "utils", "Fold utility", "NONE", "LOW: Fold."),
        ("src\\utils\\folding.ts", "utils", "Folding utility", "NONE", "LOW: Folding."),
        ("src\\utils\\forEach.ts", "utils", "For each utility", "NONE", "LOW: ForEach."),
        ("src\\utils\\force.ts", "utils", "Force utility", "NONE", "LOW: Force."),
        ("src\\utils\\foreach.ts", "utils", "Foreach utility", "NONE", "LOW: Foreach."),
        ("src\\utils\\fork.ts", "utils", "Fork utility", "NONE", "MEDIUM: Fork."),
        ("src\\utils\\form.ts", "utils", "Form utility", "NONE", "LOW: Form."),
        ("src\\utils\\fraction.ts", "utils", "Fraction utility", "NONE", "LOW: Fraction."),
        ("src\\utils\\free.ts", "utils", "Free utility", "NONE", "LOW: Free."),
        ("src\\utils\\freeze.ts", "utils", "Freeze utility", "NONE", "LOW: Freeze."),
        ("src\\utils\\from.ts", "utils", "From utility", "NONE", "LOW: From."),
        ("src\\utils\\fromAsync.ts", "utils", "From async utility", "NONE", "LOW: From async."),
        ("src\\utils\\full.ts", "utils", "Full utility", "NONE", "LOW: Full."),
        ("src\\utils\\fullscreen.ts", "utils", "Fullscreen utility", "NONE", "LOW: Fullscreen."),
        ("src\\utils\\fun.ts", "utils", "Fun utility", "NONE", "LOW: Fun."),
        ("src\\utils\\function.ts", "utils", "Function utility", "NONE", "LOW: Function."),
        ("src\\utils\\functor.ts", "utils", "Functor utility", "NONE", "LOW: Functor."),
        ("src\\utils\\gateway.ts", "utils", "Gateway utility", "NONE", "MEDIUM: Gateway."),
        ("src\\utils\\gather.ts", "utils", "Gather utility", "NONE", "LOW: Gather."),
        ("src\\utils\\gcloud.ts", "utils", "GCloud utility", "NONE", "MEDIUM: GCloud."),
        ("src\\utils\\generate.ts", "utils", "Generate utility", "NONE", "LOW: Generate."),
        ("src\\utils\\get.ts", "utils", "Get utility", "NONE", "LOW: Get."),
        ("src\\utils\\getAbsoluteTime.ts", "utils", "Get absolute time", "NONE", "LOW: Absolute time."),
        ("src\\utils\\getBaselines.ts", "utils", "Get baselines", "NONE", "MEDIUM: Baselines."),
        ("src\\utils\\getBool.ts", "utils", "Get bool", "NONE", "LOW: Get bool."),
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