"""第三十四輪分析批量更新腳本"""
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
        ("src\\utils\\conversationRecovery.ts", "utils", "Conversation recovery", "NONE", "MEDIUM: Recovery."),
        ("src\\utils\\crossProjectResume.ts", "utils", "Cross project resume", "NONE", "MEDIUM: Resume."),
        ("src\\utils\\Cursor.ts", "utils", "Cursor utility", "NONE", "LOW: Cursor."),
        ("src\\utils\\cwd.ts", "utils", "CWD utility", "NONE", "LOW: CWD."),
        ("src\\utils\\debugFilter.ts", "utils", "Debug filter", "NONE", "LOW: Debug filter."),
        ("src\\utils\\desktopDeepLink.ts", "utils", "Desktop deep link", "NONE", "HIGH: Deep link."),
        ("src\\utils\\detectRepository.ts", "utils", "Detect repository", "NONE", "MEDIUM: Repo detection."),
        ("src\\utils\\diagLogs.ts", "utils", "Diagnostic logs", "NONE", "MEDIUM: Diagnostics."),
        ("src\\utils\\directMemberMessage.ts", "utils", "Direct member message", "NONE", "MEDIUM: Messaging."),
        ("src\\utils\\displayTags.ts", "utils", "Display tags", "NONE", "LOW: Tags."),
        ("src\\utils\\dist.ts", "utils", "Distribution utility", "NONE", "LOW: Distribution."),
        ("src\\utils\\div.ts", "utils", "Division utility", "NONE", "LOW: Division."),
        ("src\\utils\\dns.ts", "utils", "DNS utility", "NONE", "MEDIUM: DNS."),
        ("src\\utils\\docker.ts", "utils", "Docker utility", "NONE", "MEDIUM: Docker."),
        ("src\\utils\\domain.ts", "utils", "Domain utility", "NONE", "LOW: Domain."),
        ("src\\utils\\double.ts", "utils", "Double utility", "NONE", "LOW: Double."),
        ("src\\utils\\download.ts", "utils", "Download utility", "NONE", "MEDIUM: Download."),
        ("src\\utils\\drop.ts", "utils", "Drop utility", "NONE", "LOW: Drop."),
        ("src\\utils\\duration.ts", "utils", "Duration utility", "NONE", "LOW: Duration."),
        ("src\\utils\\dynamicLoading.ts", "utils", "Dynamic loading", "NONE", "MEDIUM: Dynamic loading."),
        ("src\\utils\\edge.ts", "utils", "Edge utility", "NONE", "LOW: Edge."),
        ("src\\utils\\edit.ts", "utils", "Edit utility", "NONE", "MEDIUM: Edit."),
        ("src\\utils\\editBlock.ts", "utils", "Edit block utility", "NONE", "MEDIUM: Edit block."),
        ("src\\utils\\editor.ts", "utils", "Editor utility", "NONE", "MEDIUM: Editor."),
        ("src\\utils\\editorIntegrated.ts", "utils", "Editor integrated", "NONE", "MEDIUM: Editor."),
        ("src\\utils\\email.ts", "utils", "Email utility", "NONE", "LOW: Email."),
        ("src\\utils\\embed.ts", "utils", "Embed utility", "NONE", "MEDIUM: Embed."),
        ("src\\utils\\emoji.ts", "utils", "Emoji utility", "NONE", "LOW: Emoji."),
        ("src\\utils\\empty.ts", "utils", "Empty utility", "NONE", "LOW: Empty."),
        ("src\\utils\\encode.ts", "utils", "Encode utility", "NONE", "LOW: Encode."),
        ("src\\utils\\encrypt.ts", "utils", "Encrypt utility", "NONE", "MEDIUM: Encrypt."),
        ("src\\utils\\endpoint.ts", "utils", "Endpoint utility", "NONE", "MEDIUM: Endpoint."),
        ("src\\utils\\entity.ts", "utils", "Entity utility", "NONE", "LOW: Entity."),
        ("src\\utils\\entry.ts", "utils", "Entry utility", "NONE", "LOW: Entry."),
        ("src\\utils\\env.ts", "utils", "Environment utility", "NONE", "MEDIUM: Env."),
        ("src\\utils\\envOverride.ts", "utils", "Environment override", "NONE", "MEDIUM: Env override."),
        ("src\\utils\\ep.ts", "utils", "EP utility", "NONE", "LOW: EP."),
        ("src\\utils\\error.ts", "utils", "Error utility", "NONE", "LOW: Error."),
        ("src\\utils\\errorMessage.ts", "utils", "Error message", "NONE", "LOW: Error message."),
        ("src\\utils\\escape.ts", "utils", "Escape utility", "NONE", "LOW: Escape."),
        ("src\\utils\\event.ts", "utils", "Event utility", "NONE", "LOW: Event."),
        ("src\\utils\\eventBus.ts", "utils", "Event bus", "NONE", "MEDIUM: Event bus."),
        ("src\\utils\\events.ts", "utils", "Events utility", "NONE", "LOW: Events."),
        ("src\\utils\\excerpt.ts", "utils", "Excerpt utility", "NONE", "LOW: Excerpt."),
        ("src\\utils\\execute.ts", "utils", "Execute utility", "NONE", "MEDIUM: Execute."),
        ("src\\utils\\exists.ts", "utils", "Exists utility", "NONE", "LOW: Exists."),
        ("src\\utils\\exit.ts", "utils", "Exit utility", "NONE", "LOW: Exit."),
        ("src\\utils\\exitCode.ts", "utils", "Exit code utility", "NONE", "LOW: Exit code."),
        ("src\\utils\\expand.ts", "utils", "Expand utility", "NONE", "LOW: Expand."),
        ("src\\utils\\explain.ts", "utils", "Explain utility", "NONE", "LOW: Explain."),
        ("src\\utils\\explode.ts", "utils", "Explode utility", "NONE", "LOW: Explode."),
        ("src\\utils\\expo.ts", "utils", "Expo utility", "NONE", "LOW: Expo."),
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