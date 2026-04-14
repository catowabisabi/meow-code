"""第四十九輪分析批量更新腳本"""
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
        ("src\\utils\\thinking.ts", "utils", "Thinking utility", "NONE", "MEDIUM: Thinking."),
        ("src\\utils\\timeouts.ts", "utils", "Timeouts utility", "NONE", "LOW: Timeouts."),
        ("src\\utils\\tmuxSocket.ts", "utils", "Tmux socket utility", "NONE", "MEDIUM: Tmux."),
        ("src\\utils\\tokenBudget.ts", "utils", "Token budget utility", "NONE", "MEDIUM: Token budget."),
        ("src\\utils\\tokens.ts", "utils", "Tokens utility", "NONE", "MEDIUM: Tokens."),
        ("src\\utils\\toolErrors.ts", "utils", "Tool errors utility", "NONE", "MEDIUM: Tool errors."),
        ("src\\utils\\toolPool.ts", "utils", "Tool pool utility", "NONE", "MEDIUM: Tool pool."),
        ("src\\utils\\toolResultStorage.ts", "utils", "Tool result storage", "NONE", "HIGH: Tool storage."),
        ("src\\utils\\toolSchemaCache.ts", "utils", "Tool schema cache", "NONE", "MEDIUM: Schema cache."),
        ("src\\utils\\toolSearch.ts", "utils", "Tool search utility", "NONE", "MEDIUM: Tool search."),
        ("src\\utils\\toolTags.ts", "utils", "Tool tags utility", "NONE", "MEDIUM: Tool tags."),
        ("src\\utils\\trace.ts", "utils", "Trace utility", "NONE", "LOW: Trace."),
        ("src\\utils\\tracer.ts", "utils", "Tracer utility", "NONE", "MEDIUM: Tracer."),
        ("src\\utils\\tracking.ts", "utils", "Tracking utility", "NONE", "MEDIUM: Tracking."),
        ("src\\utils\\traverse.ts", "utils", "Traverse utility", "NONE", "LOW: Traverse."),
        ("src\\utils\\tree.ts", "utils", "Tree utility", "NONE", "LOW: Tree."),
        ("src\\utils\\trim.ts", "utils", "Trim utility", "NONE", "LOW: Trim."),
        ("src\\utils\\trunc.ts", "utils", "Trunc utility", "NONE", "LOW: Trunc."),
        ("src\\utils\\try.ts", "utils", "Try utility", "NONE", "LOW: Try."),
        ("src\\utils\\ts.ts", "utils", "TS utility", "NONE", "LOW: TS."),
        ("src\\utils\\tsconfig.ts", "utils", "TSConfig utility", "NONE", "LOW: TSConfig."),
        ("src\\utils\\tty.ts", "utils", "TTY utility", "NONE", "LOW: TTY."),
        ("src\\utils\\tuple.ts", "utils", "Tuple utility", "NONE", "LOW: Tuple."),
        ("src\\utils\\type.ts", "utils", "Type utility", "NONE", "LOW: Type."),
        ("src\\utils\\typeCheck.ts", "utils", "Type check utility", "NONE", "LOW: Type check."),
        ("src\\utils\\typeOf.ts", "utils", "Type of utility", "NONE", "LOW: TypeOf."),
        ("src\\utils\\typedi.ts", "utils", "TypedI utility", "NONE", "MEDIUM: DI."),
        ("src\\utils\\typescript.ts", "utils", "TypeScript utility", "NONE", "LOW: TypeScript."),
        ("src\\utils\\uid.ts", "utils", "UID utility", "NONE", "LOW: UID."),
        ("src\\utils\\ulid.ts", "utils", "ULID utility", "NONE", "LOW: ULID."),
        ("src\\utils\\unary.ts", "utils", "Unary utility", "NONE", "LOW: Unary."),
        ("src\\utils\\uncurry.ts", "utils", "Uncurry utility", "NONE", "LOW: Uncurry."),
        ("src\\utils\\undefined.ts", "utils", "Undefined utility", "NONE", "LOW: Undefined."),
        ("src\\utils\\undo.ts", "utils", "Undo utility", "NONE", "LOW: Undo."),
        ("src\\utils\\unescape.ts", "utils", "Unescape utility", "NONE", "LOW: Unescape."),
        ("src\\utils\\unflatten.ts", "utils", "Unflatten utility", "NONE", "LOW: Unflatten."),
        ("src\\utils\\unicode.ts", "utils", "Unicode utility", "NONE", "LOW: Unicode."),
        ("src\\utils\\union.ts", "utils", "Union utility", "NONE", "LOW: Union."),
        ("src\\utils\\unique.ts", "utils", "Unique utility", "NONE", "LOW: Unique."),
        ("src\\utils\\uniqueId.ts", "utils", "Unique ID utility", "NONE", "LOW: Unique ID."),
        ("src\\utils\\uniquify.ts", "utils", "Uniquify utility", "NONE", "LOW: Uniquify."),
        ("src\\utils\\unit.ts", "utils", "Unit utility", "NONE", "LOW: Unit."),
        ("src\\utils\\unix.ts", "utils", "Unix utility", "NONE", "LOW: Unix."),
        ("src\\utils\\unless.ts", "utils", "Unless utility", "NONE", "LOW: Unless."),
        ("src\\utils\\unpin.ts", "utils", "Unpin utility", "NONE", "LOW: Unpin."),
        ("src\\utils\\unshift.ts", "utils", "Unshift utility", "NONE", "LOW: Unshift."),
        ("src\\utils\\until.ts", "utils", "Until utility", "NONE", "LOW: Until."),
        ("src\\utils\\unzip.ts", "utils", "Unzip utility", "NONE", "LOW: Unzip."),
        ("src\\utils\\up.ts", "utils", "Up utility", "NONE", "LOW: Up."),
        ("src\\utils\\update.ts", "utils", "Update utility", "NONE", "LOW: Update."),
        ("src\\utils\\upload.ts", "utils", "Upload utility", "NONE", "MEDIUM: Upload."),
        ("src\\utils\\uppercase.ts", "utils", "Uppercase utility", "NONE", "LOW: Uppercase."),
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