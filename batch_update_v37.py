"""第三十七輪分析批量更新腳本"""
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
        ("src\\utils\\findExecutable.ts", "utils", "Find executable", "NONE", "MEDIUM: Find executable."),
        ("src\\utils\\fingerprint.ts", "utils", "Fingerprint utility", "NONE", "MEDIUM: Fingerprint."),
        ("src\\utils\\forkedAgent.ts", "utils", "Forked agent", "NONE", "HIGH: Forked agent."),
        ("src\\utils\\fpsTracker.ts", "utils", "FPS tracker", "NONE", "LOW: FPS tracker."),
        ("src\\utils\\frontmatterParser.ts", "utils", "Frontmatter parser", "NONE", "LOW: Frontmatter."),
        ("src\\utils\\fsOperations.ts", "utils", "Filesystem operations", "NONE", "MEDIUM: FS operations."),
        ("src\\utils\\generatedFiles.ts", "utils", "Generated files", "NONE", "MEDIUM: Generated files."),
        ("src\\utils\\generators.ts", "utils", "Generators utility", "NONE", "LOW: Generators."),
        ("src\\utils\\genericProcessUtils.ts", "utils", "Generic process utils", "NONE", "MEDIUM: Process utils."),
        ("src\\utils\\getWorktreePaths.ts", "utils", "Get worktree paths", "NONE", "HIGH: Worktree paths."),
        ("src\\utils\\git.ts", "utils", "Git utility", "NONE", "MEDIUM: Git."),
        ("src\\utils\\gitignore.ts", "utils", "Gitignore utility", "NONE", "LOW: Gitignore."),
        ("src\\utils\\gitOperations.ts", "utils", "Git operations", "NONE", "MEDIUM: Git ops."),
        ("src\\utils\\gitRef.ts", "utils", "Git ref utility", "NONE", "LOW: Git ref."),
        ("src\\utils\\global.ts", "utils", "Global utility", "NONE", "LOW: Global."),
        ("src\\utils\\group.ts", "utils", "Group utility", "NONE", "LOW: Group."),
        ("src\\utils\\groupBy.ts", "utils", "Group by utility", "NONE", "LOW: GroupBy."),
        ("src\\utils\\guard.ts", "utils", "Guard utility", "NONE", "LOW: Guard."),
        ("src\\utils\\h.ts", "utils", "H utility", "NONE", "LOW: H."),
        ("src\\utils\\handleENOENT.ts", "utils", "Handle ENOENT", "NONE", "LOW: Error handling."),
        ("src\\utils\\has.ts", "utils", "Has utility", "NONE", "LOW: Has."),
        ("src\\utils\\hasAccessibleWindow.ts", "utils", "Has accessible window", "NONE", "LOW: Window."),
        ("src\\utils\\hash.ts", "utils", "Hash utility", "NONE", "LOW: Hash."),
        ("src\\utils\\hashText.ts", "utils", "Hash text", "NONE", "LOW: Hash text."),
        ("src\\utils\\hasOwnProperty.ts", "utils", "Has own property", "NONE", "LOW: Property."),
        ("src\\utils\\head.ts", "utils", "Head utility", "NONE", "LOW: Head."),
        ("src\\utils\\health.ts", "utils", "Health utility", "NONE", "MEDIUM: Health."),
        ("src\\utils\\heap.ts", "utils", "Heap utility", "NONE", "LOW: Heap."),
        ("src\\utils\\heapSnapshot.ts", "utils", "Heap snapshot", "NONE", "MEDIUM: Heap snapshot."),
        ("src\\utils\\help.ts", "utils", "Help utility", "NONE", "LOW: Help."),
        ("src\\utils\\hide.ts", "utils", "Hide utility", "NONE", "LOW: Hide."),
        ("src\\utils\\homedir.ts", "utils", "Home directory", "NONE", "LOW: Home dir."),
        ("src\\utils\\hook.ts", "utils", "Hook utility", "NONE", "MEDIUM: Hook."),
        ("src\\utils\\host.ts", "utils", "Host utility", "NONE", "LOW: Host."),
        ("src\\utils\\hostname.ts", "utils", "Hostname utility", "NONE", "LOW: Hostname."),
        ("src\\utils\\hours.ts", "utils", "Hours utility", "NONE", "LOW: Hours."),
        ("src\\utils\\id.ts", "utils", "ID utility", "NONE", "LOW: ID."),
        ("src\\utils\\identity.ts", "utils", "Identity utility", "NONE", "LOW: Identity."),
        ("src\\utils\\ignore.ts", "utils", "Ignore utility", "NONE", "LOW: Ignore."),
        ("src\\utils\\image.ts", "utils", "Image utility", "NONE", "LOW: Image."),
        ("src\\utils\\imageUrl.ts", "utils", "Image URL utility", "NONE", "LOW: Image URL."),
        ("src\\utils\\imap.ts", "utils", "IMAP utility", "NONE", "MEDIUM: IMAP."),
        ("src\\utils\\immutable.ts", "utils", "Immutable utility", "NONE", "LOW: Immutable."),
        ("src\\utils\\implies.ts", "utils", "Implies utility", "NONE", "LOW: Implies."),
        ("src\\utils\\inCato.ts", "utils", "In Cato check", "NONE", "LOW: Cato check."),
        ("src\\utils\\inDirectory.ts", "utils", "In directory check", "NONE", "LOW: Directory check."),
        ("src\\utils\\index.ts", "utils", "Index utility", "NONE", "LOW: Index."),
        ("src\\utils\\init.ts", "utils", "Init utility", "NONE", "LOW: Init."),
        ("src\\utils\\initial.ts", "utils", "Initial utility", "NONE", "LOW: Initial."),
        ("src\\utils\\inline.ts", "utils", "Inline utility", "NONE", "LOW: Inline."),
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