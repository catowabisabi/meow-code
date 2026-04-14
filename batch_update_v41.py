"""第四十一輪分析批量更新腳本"""
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
        ("src\\utils\\logoV2Utils.ts", "utils", "Logo V2 utils", "NONE", "LOW: Logo."),
        ("src\\utils\\mailbox.ts", "utils", "Mailbox utility", "NONE", "LOW: Mailbox."),
        ("src\\utils\\managedEnv.ts", "utils", "Managed env", "NONE", "MEDIUM: Managed env."),
        ("src\\utils\\managedEnvConstants.ts", "utils", "Managed env constants", "NONE", "MEDIUM: Env constants."),
        ("src\\utils\\markdown.ts", "utils", "Markdown utility", "NONE", "LOW: Markdown."),
        ("src\\utils\\markdownConfigLoader.ts", "utils", "Markdown config loader", "NONE", "MEDIUM: Config loader."),
        ("src\\utils\\mcpInstructionsDelta.ts", "utils", "MCP instructions delta", "NONE", "HIGH: MCP delta."),
        ("src\\utils\\mcpOutputStorage.ts", "utils", "MCP output storage", "NONE", "HIGH: MCP storage."),
        ("src\\utils\\mcpWebSocketTransport.ts", "utils", "MCP WebSocket transport", "NONE", "HIGH: MCP transport."),
        ("src\\utils\\memoize.ts", "utils", "Memoize utility", "NONE", "LOW: Memoize."),
        ("src\\utils\\memory.ts", "utils", "Memory utility", "NONE", "MEDIUM: Memory."),
        ("src\\utils\\merge.ts", "utils", "Merge utility", "NONE", "LOW: Merge."),
        ("src\\utils\\message.ts", "utils", "Message utility", "NONE", "LOW: Message."),
        ("src\\utils\\messageBus.ts", "utils", "Message bus", "NONE", "MEDIUM: Message bus."),
        ("src\\utils\\meta.ts", "utils", "Meta utility", "NONE", "LOW: Meta."),
        ("src\\utils\\metrics.ts", "utils", "Metrics utility", "NONE", "MEDIUM: Metrics."),
        ("src\\utils\\micro.ts", "utils", "Micro utility", "NONE", "LOW: Micro."),
        ("src\\utils\\min.ts", "utils", "Min utility", "NONE", "LOW: Min."),
        ("src\\utils\\minus.ts", "utils", "Minus utility", "NONE", "LOW: Minus."),
        ("src\\utils\\mkdir.ts", "utils", "Mkdir utility", "NONE", "LOW: Mkdir."),
        ("src\\utils\\mktemp.ts", "utils", "Mkstemp utility", "NONE", "LOW: Mktemp."),
        ("src\\utils\\mode.ts", "utils", "Mode utility", "NONE", "LOW: Mode."),
        ("src\\utils\\model.ts", "utils", "Model utility", "NONE", "MEDIUM: Model."),
        ("src\\utils\\modelApiConstants.ts", "utils", "Model API constants", "NONE", "MEDIUM: API constants."),
        ("src\\utils\\modelHelpers.ts", "utils", "Model helpers", "NONE", "MEDIUM: Model helpers."),
        ("src\\utils\\modeling.ts", "utils", "Modeling utility", "NONE", "MEDIUM: Modeling."),
        ("src\\utils\\modem.ts", "utils", "Modem utility", "NONE", "LOW: Modem."),
        ("src\\utils\\modules.ts", "utils", "Modules utility", "NONE", "LOW: Modules."),
        ("src\\utils\\monitor.ts", "utils", "Monitor utility", "NONE", "MEDIUM: Monitor."),
        ("src\\utils\\monotonic.ts", "utils", "Monotonic utility", "NONE", "LOW: Monotonic."),
        ("src\\utils\\months.ts", "utils", "Months utility", "NONE", "LOW: Months."),
        ("src\\utils\\more.ts", "utils", "More utility", "NONE", "LOW: More."),
        ("src\\utils\\mount.ts", "utils", "Mount utility", "NONE", "LOW: Mount."),
        ("src\\utils\\mouse.ts", "utils", "Mouse utility", "NONE", "LOW: Mouse."),
        ("src\\utils\\move.ts", "utils", "Move utility", "NONE", "LOW: Move."),
        ("src\\utils\\movement.ts", "utils", "Movement utility", "NONE", "LOW: Movement."),
        ("src\\utils\\multicast.ts", "utils", "Multicast utility", "NONE", "LOW: Multicast."),
        ("src\\utils\\multiline.ts", "utils", "Multiline utility", "NONE", "LOW: Multiline."),
        ("src\\utils\\multipart.ts", "utils", "Multipart utility", "NONE", "MEDIUM: Multipart."),
        ("src\\utils\\mustache.ts", "utils", "Mustache utility", "NONE", "LOW: Mustache."),
        ("src\\utils\\mutate.ts", "utils", "Mutate utility", "NONE", "LOW: Mutate."),
        ("src\\utils\\mysql.ts", "utils", "MySQL utility", "NONE", "MEDIUM: MySQL."),
        ("src\\utils\\name.ts", "utils", "Name utility", "NONE", "LOW: Name."),
        ("src\\utils\\namespace.ts", "utils", "Namespace utility", "NONE", "LOW: Namespace."),
        ("src\\utils\\nan.ts", "utils", "NaN utility", "NONE", "LOW: NaN."),
        ("src\\utils\\negate.ts", "utils", "Negate utility", "NONE", "LOW: Negate."),
        ("src\\utils\\net.ts", "utils", "Net utility", "NONE", "MEDIUM: Net."),
        ("src\\utils\\network.ts", "utils", "Network utility", "NONE", "MEDIUM: Network."),
        ("src\\utils\\never.ts", "utils", "Never utility", "NONE", "LOW: Never."),
        ("src\\utils\\new.ts", "utils", "New utility", "NONE", "LOW: New."),
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