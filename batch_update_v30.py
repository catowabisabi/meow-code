"""第三十輪分析批量更新腳本 - utils 目錄 continuation"""
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
        ("src\\utils\\appleTerminalBackup.ts", "utils", "Apple Terminal backup", "NONE", "LOW: Apple Terminal."),
        ("src\\utils\\argumentSubstitution.ts", "utils", "Argument substitution", "NONE", "MEDIUM: Args."),
        ("src\\utils\\asciicast.ts", "utils", "Asciicast utilities", "NONE", "MEDIUM: Asciicast."),
        ("src\\utils\\attachments.ts", "utils", "Attachments utilities", "NONE", "MEDIUM: Attachments."),
        ("src\\utils\\attribution.ts", "utils", "Attribution utilities", "NONE", "LOW: Attribution."),
        ("src\\utils\\authFileDescriptor.ts", "utils", "Auth file descriptor", "NONE", "HIGH: Auth."),
        ("src\\utils\\authPortable.ts", "utils", "Auth portable", "NONE", "HIGH: Auth portable."),
        ("src\\utils\\autoModeDenials.ts", "utils", "Auto mode denials tracking", "NONE", "HIGH: Auto mode."),
        ("src\\utils\\autoUpdater.ts", "utils", "Auto updater", "NONE", "HIGH: Auto update."),
        ("src\\utils\\awsAuthStatusManager.ts", "utils", "AWS auth status manager", "NONE", "HIGH: AWS auth."),
        ("src\\utils\\backoff.ts", "utils", "Backoff utility", "NONE", "LOW: Backoff."),
        ("src\\utils\\base64.ts", "utils", "Base64 encoding", "NONE", "LOW: Base64."),
        ("src\\utils\\bdist.ts", "utils", "Binary distribution", "NONE", "LOW: Distribution."),
        ("src\\utils\\bench.ts", "utils", "Benchmark utility", "NONE", "LOW: Benchmark."),
        ("src\\utils\\beta.ts", "utils", "Beta utilities", "NONE", "LOW: Beta."),
        ("src\\utils\\bigintUtil.ts", "utils", "BigInt utilities", "NONE", "LOW: BigInt."),
        ("src\\utils\\binaryInsert.ts", "utils", "Binary insert", "NONE", "LOW: Binary insert."),
        ("src\\utils\\bit.ts", "utils", "Bit utilities", "NONE", "LOW: Bit."),
        ("src\\utils\\bitset.ts", "utils", "Bitset utility", "NONE", "LOW: Bitset."),
        ("src\\utils\\blackbox.ts", "utils", "Blackbox utilities", "NONE", "MEDIUM: Blackbox."),
        ("src\\utils\\block.ts", "utils", "Block utilities", "NONE", "LOW: Block."),
        ("src\\utils\\boolean.ts", "utils", "Boolean utilities", "NONE", "LOW: Boolean."),
        ("src\\utils\\bracket.ts", "utils", "Bracket utilities", "NONE", "LOW: Bracket."),
        ("src\\utils\\brand.ts", "utils", "Brand utilities", "NONE", "LOW: Brand."),
        ("src\\utils\\breakdown.ts", "utils", "Breakdown utility", "NONE", "LOW: Breakdown."),
        ("src\\utils\\broadcaster.ts", "utils", "Broadcaster utility", "NONE", "LOW: Broadcaster."),
        ("src\\utils\\bundlers.ts", "utils", "Bundlers utility", "NONE", "MEDIUM: Bundlers."),
        ("src\\utils\\cached.ts", "utils", "Cached utility", "NONE", "MEDIUM: Cached."),
        ("src\\utils\\capture.ts", "utils", "Capture utility", "NONE", "LOW: Capture."),
        ("src\\utils\\cast.ts", "utils", "Cast utility", "NONE", "LOW: Cast."),
        ("src\\utils\\catchup.ts", "utils", "Catchup utility", "NONE", "LOW: Catchup."),
        ("src\\utils\\ceil.ts", "utils", "Ceiling utility", "NONE", "LOW: Ceil."),
        ("src\\utils\\change.ts", "utils", "Change utility", "NONE", "LOW: Change."),
        ("src\\utils\\channel.ts", "utils", "Channel utility", "NONE", "MEDIUM: Channel."),
        ("src\\utils\\charge.ts", "utils", "Charge utility", "NONE", "LOW: Charge."),
        ("src\\utils\\chat.ts", "utils", "Chat utility", "NONE", "MEDIUM: Chat."),
        ("src\\utils\\check.ts", "utils", "Check utility", "NONE", "LOW: Check."),
        ("src\\utils\\checksum.ts", "utils", "Checksum utility", "NONE", "LOW: Checksum."),
        ("src\\utils\\cid.ts", "utils", "CID utility", "NONE", "LOW: CID."),
        ("src\\utils\\circular.ts", "utils", "Circular reference detection", "NONE", "LOW: Circular."),
        ("src\\utils\\claim.ts", "utils", "Claim utility", "NONE", "LOW: Claim."),
        ("src\\utils\\clamp.ts", "utils", "Clamp utility", "NONE", "LOW: Clamp."),
        ("src\\utils\\classify.ts", "utils", "Classify utility", "NONE", "LOW: Classify."),
        ("src\\utils\\clear.ts", "utils", "Clear utility", "NONE", "LOW: Clear."),
        ("src\\utils\\cli.ts", "utils", "CLI utilities", "NONE", "MEDIUM: CLI."),
        ("src\\utils\\clipboard.ts", "utils", "Clipboard utilities", "NONE", "MEDIUM: Clipboard."),
        ("src\\utils\\clone.ts", "utils", "Clone utility", "NONE", "LOW: Clone."),
        ("src\\utils\\close.ts", "utils", "Close utility", "NONE", "LOW: Close."),
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