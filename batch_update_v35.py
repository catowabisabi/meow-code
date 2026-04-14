"""第三十五輪分析批量更新腳本"""
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
        ("src\\utils\\doctorContextWarnings.ts", "utils", "Doctor context warnings", "NONE", "MEDIUM: Doctor."),
        ("src\\utils\\doctorDiagnostic.ts", "utils", "Doctor diagnostic", "NONE", "MEDIUM: Doctor."),
        ("src\\utils\\earlyInput.ts", "utils", "Early input", "NONE", "LOW: Input."),
        ("src\\utils\\effort.ts", "utils", "Effort utility", "NONE", "LOW: Effort."),
        ("src\\utils\\embeddedTools.ts", "utils", "Embedded tools", "NONE", "MEDIUM: Tools."),
        ("src\\utils\\envDynamic.ts", "utils", "Dynamic env", "NONE", "MEDIUM: Env."),
        ("src\\utils\\envUtils.ts", "utils", "Env utilities", "NONE", "MEDIUM: Env utils."),
        ("src\\utils\\envValidation.ts", "utils", "Env validation", "NONE", "MEDIUM: Env validation."),
        ("src\\utils\\errorLogSink.ts", "utils", "Error log sink", "NONE", "MEDIUM: Error logging."),
        ("src\\utils\\exampleCommands.ts", "utils", "Example commands", "NONE", "LOW: Examples."),
        ("src\\utils\\exec.ts", "utils", "Exec utility", "NONE", "MEDIUM: Exec."),
        ("src\\utils\\execSync.ts", "utils", "Exec sync", "NONE", "MEDIUM: Exec sync."),
        ("src\\utils\\execute.ts", "utils", "Execute utility", "NONE", "MEDIUM: Execute."),
        ("src\\utils\\exit.ts", "utils", "Exit utility", "NONE", "LOW: Exit."),
        ("src\\utils\\expand.ts", "utils", "Expand utility", "NONE", "LOW: Expand."),
        ("src\\utils\\explain.ts", "utils", "Explain utility", "NONE", "LOW: Explain."),
        ("src\\utils\\explode.ts", "utils", "Explode utility", "NONE", "LOW: Explode."),
        ("src\\utils\\expo.ts", "utils", "Expo utility", "NONE", "LOW: Expo."),
        ("src\\utils\\extract.ts", "utils", "Extract utility", "NONE", "LOW: Extract."),
        ("src\\utils\\fallback.ts", "utils", "Fallback utility", "NONE", "LOW: Fallback."),
        ("src\\utils\\false.ts", "utils", "False utility", "NONE", "LOW: False."),
        ("src\\utils\\family.ts", "utils", "Family utility", "NONE", "LOW: Family."),
        ("src\\utils\\feature.ts", "utils", "Feature utility", "NONE", "LOW: Feature."),
        ("src\\utils\\featureGate.ts", "utils", "Feature gate", "NONE", "MEDIUM: Feature gate."),
        ("src\\utils\\fetch.ts", "utils", "Fetch utility", "NONE", "MEDIUM: Fetch."),
        ("src\\utils\\file.ts", "utils", "File utility", "NONE", "MEDIUM: File."),
        ("src\\utils\\fileExists.ts", "utils", "File exists", "NONE", "LOW: File exists."),
        ("src\\utils\\fileUrl.ts", "utils", "File URL", "NONE", "LOW: File URL."),
        ("src\\utils\\filter.ts", "utils", "Filter utility", "NONE", "LOW: Filter."),
        ("src\\utils\\find.ts", "utils", "Find utility", "NONE", "LOW: Find."),
        ("src\\utils\\findAll.ts", "utils", "Find all", "NONE", "LOW: Find all."),
        ("src\\utils\\findUp.ts", "utils", "Find up", "NONE", "LOW: Find up."),
        ("src\\utils\\first.ts", "utils", "First utility", "NONE", "LOW: First."),
        ("src\\utils\\flat.ts", "utils", "Flat utility", "NONE", "LOW: Flat."),
        ("src\\utils\\flatMap.ts", "utils", "Flat map", "NONE", "LOW: Flat map."),
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
        ("src\\utils\\forEach.ts", "utils", "For each", "NONE", "LOW: ForEach."),
        ("src\\utils\\force.ts", "utils", "Force utility", "NONE", "LOW: Force."),
        ("src\\utils\\foreach.ts", "utils", "Foreach utility", "NONE", "LOW: Foreach."),
        ("src\\utils\\fork.ts", "utils", "Fork utility", "NONE", "MEDIUM: Fork."),
        ("src\\utils\\form.ts", "utils", "Form utility", "NONE", "LOW: Form."),
        ("src\\utils\\format.ts", "utils", "Format utility", "NONE", "LOW: Format."),
        ("src\\utils\\fraction.ts", "utils", "Fraction utility", "NONE", "LOW: Fraction."),
        ("src\\utils\\free.ts", "utils", "Free utility", "NONE", "LOW: Free."),
        ("src\\utils\\freeze.ts", "utils", "Freeze utility", "NONE", "LOW: Freeze."),
        ("src\\utils\\from.ts", "utils", "From utility", "NONE", "LOW: From."),
        ("src\\utils\\fromAsync.ts", "utils", "From async", "NONE", "LOW: From async."),
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