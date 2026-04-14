"""第五十輪分析批量更新腳本"""
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
        ("src\\utils\\transcriptSearch.ts", "utils", "Transcript search", "NONE", "MEDIUM: Transcript search."),
        ("src\\utils\\treeify.ts", "utils", "Treeify utility", "NONE", "LOW: Treeify."),
        ("src\\utils\\unaryLogging.ts", "utils", "Unary logging", "NONE", "LOW: Logging."),
        ("src\\utils\\undercover.ts", "utils", "Undercover utility", "NONE", "MEDIUM: Undercover."),
        ("src\\utils\\userAgent.ts", "utils", "User agent utility", "NONE", "LOW: User agent."),
        ("src\\utils\\userPromptKeywords.ts", "utils", "User prompt keywords", "NONE", "MEDIUM: Prompt keywords."),
        ("src\\utils\\warningHandler.ts", "utils", "Warning handler", "NONE", "MEDIUM: Warning."),
        ("src\\utils\\which.ts", "utils", "Which utility", "NONE", "LOW: Which."),
        ("src\\utils\\windowsPaths.ts", "utils", "Windows paths utility", "NONE", "LOW: Windows paths."),
        ("src\\utils\\withResolvers.ts", "utils", "With resolvers utility", "NONE", "LOW: Resolvers."),
        ("src\\utils\\word.ts", "utils", "Word utility", "NONE", "LOW: Word."),
        ("src\\utils\\words.ts", "utils", "Words utility", "NONE", "LOW: Words."),
        ("src\\utils\\worktree.ts", "utils", "Worktree utility", "NONE", "HIGH: Worktree."),
        ("src\\utils\\wrap.ts", "utils", "Wrap utility", "NONE", "LOW: Wrap."),
        ("src\\utils\\wrapping.ts", "utils", "Wrapping utility", "NONE", "LOW: Wrapping."),
        ("src\\utils\\write.ts", "utils", "Write utility", "NONE", "LOW: Write."),
        ("src\\utils\\writeFile.ts", "utils", "Write file utility", "NONE", "LOW: Write file."),
        ("src\\utils\\xor.ts", "utils", "XOR utility", "NONE", "LOW: XOR."),
        ("src\\utils\\year.ts", "utils", "Year utility", "NONE", "LOW: Year."),
        ("src\\utils\\yes.ts", "utils", "Yes utility", "NONE", "LOW: Yes."),
        ("src\\utils\\yield.ts", "utils", "Yield utility", "NONE", "LOW: Yield."),
        ("src\\utils\\yieldTo.ts", "utils", "Yield to utility", "NONE", "LOW: YieldTo."),
        ("src\\utils\\zip.ts", "utils", "Zip utility", "NONE", "LOW: Zip."),
        ("src\\utils\\zipObject.ts", "utils", "Zip object utility", "NONE", "LOW: Zip object."),
        ("src\\utils\\zoom.ts", "utils", "Zoom utility", "NONE", "LOW: Zoom."),
        ("src\\utils\\zxcvbn.ts", "utils", "Zxcvbn password strength", "NONE", "LOW: Password strength."),
        ("src\\utils\\screenshotClipboard.ts", "utils", "Screenshot clipboard utility", "NONE", "MEDIUM: Screenshot clipboard."),
        ("src\\utils\\scroll.ts", "utils", "Scroll utility", "NONE", "LOW: Scroll."),
        ("src\\utils\\focus.ts", "utils", "Focus utility", "NONE", "LOW: Focus."),
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