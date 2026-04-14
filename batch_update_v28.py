"""第二十八輪分析批量更新腳本 - commands plugin, review, stats"""
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
        ("src\\commands\\plugin\\usePagination.ts", "commands/plugin", "Plugin pagination hook", "NONE", "LOW: Pagination."),
        ("src\\commands\\pr_comments\\index.ts", "commands/pr_comments", "PR comments index", "NONE", "LOW: Index."),
        ("src\\commands\\privacy-settings\\privacy-settings.tsx", "commands/privacy", "Privacy settings UI", "NONE", "HIGH: Privacy settings."),
        ("src\\commands\\rate-limit-options\\index.ts", "commands/rate-limit", "Rate limit index", "NONE", "LOW: Index."),
        ("src\\commands\\rate-limit-options\\rate-limit-options.tsx", "commands/rate-limit", "Rate limit options UI", "NONE", "MEDIUM: Rate limiting."),
        ("src\\commands\\release-notes\\index.ts", "commands/release-notes", "Release notes index", "NONE", "LOW: Index."),
        ("src\\commands\\reload-plugins\\index.ts", "commands/reload-plugins", "Reload plugins index", "NONE", "LOW: Index."),
        ("src\\commands\\reload-plugins\\reload-plugins.ts", "commands/reload-plugins", "Reload plugins command", "NONE", "MEDIUM: Plugin reload."),
        ("src\\commands\\remote-env\\index.ts", "commands/remote-env", "Remote env index", "NONE", "LOW: Index."),
        ("src\\commands\\remote-env\\remote-env.tsx", "commands/remote-env", "Remote env UI", "NONE", "MEDIUM: Remote env."),
        ("src\\commands\\remote-setup\\remote-setup.tsx", "commands/remote-setup", "Remote setup UI", "NONE", "HIGH: Remote setup."),
        ("src\\commands\\rename\\generateSessionName.ts", "commands/rename", "Generate session name", "NONE", "LOW: Name gen."),
        ("src\\commands\\rename\\index.ts", "commands/rename", "Rename index", "NONE", "LOW: Index."),
        ("src\\commands\\rename\\rename.ts", "commands/rename", "Rename command", "NONE", "MEDIUM: Rename."),
        ("src\\commands\\resume\\resume.tsx", "commands/resume", "Resume command UI", "NONE", "MEDIUM: Resume."),
        ("src\\commands\\review\\UltrareviewOverageDialog.tsx", "commands/review", "Ultrareview overage dialog", "NONE", "HIGH: Ultrareview."),
        ("src\\commands\\review\\reviewRemote.ts", "commands/review", "Review remote", "NONE", "HIGH: Review remote."),
        ("src\\commands\\review\\ultrareviewCommand.tsx", "commands/review", "Ultrareview command UI", "NONE", "HIGH: Ultrareview."),
        ("src\\commands\\review\\ultrareviewEnabled.ts", "commands/review", "Ultrareview enabled check", "NONE", "HIGH: Ultrareview."),
        ("src\\commands\\rewind\\index.ts", "commands/rewind", "Rewind index", "NONE", "LOW: Index."),
        ("src\\commands\\sandbox-toggle\\sandbox-toggle.tsx", "commands/sandbox", "Sandbox toggle UI", "NONE", "HIGH: Sandbox toggle."),
        ("src\\commands\\session\\session.tsx", "commands/session", "Session command UI", "NONE", "MEDIUM: Session."),
        ("src\\commands\\skills\\skills.tsx", "commands/skills", "Skills command UI", "NONE", "HIGH: Skills command."),
        ("src\\commands\\stats\\index.ts", "commands/stats", "Stats index", "NONE", "LOW: Index."),
        ("src\\commands\\stats\\stats.tsx", "commands/stats", "Stats UI", "NONE", "LOW: Stats."),
        ("src\\commands\\status\\index.ts", "commands/status", "Status index", "NONE", "LOW: Index."),
        ("src\\commands\\status\\status.tsx", "commands/status", "Status UI", "NONE", "LOW: Status."),
        ("src\\commands\\statusline.tsx", "commands/statusline", "Statusline component", "NONE", "LOW: Statusline."),
        ("src\\commands\\stickers\\index.ts", "commands/stickers", "Stickers index", "NONE", "LOW: Index."),
        ("src\\commands\\stickers\\stickers.ts", "commands/stickers", "Stickers command", "NONE", "LOW: Stickers."),
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