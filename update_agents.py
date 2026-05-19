import psycopg2
import json

conn = psycopg2.connect(host='postgres', port=5432, database='clawith', user='clawith', password='clawith')
cur = conn.cursor()

MODEL_ID = "44f7ef15-9d3b-4c47-bcd4-435467fd6d64"
AUTONOMY_POLICY = {
    "read_files": "L1",
    "write_workspace_files": "L2",
    "send_feishu_message": "L2",
    "send_external_message": "L2",
    "modify_soul": "L3",
    "access_business_system_read": "L1",
    "access_business_system_write": "L1",
    "delete_files": "L2",
    "create_calendar_event": "L2",
    "financial_operations": "L3"
}

NAME_PREFIXES = {
    "AI 工程師 A": "Alex",
    "API 整合工程師": "Brian",
    "DevOps 工程師": "Chris",
    "UI 設計師": "Diana",
    "UX 設計師": "Evan",
    "人事行政": "Fiona",
    "內容行銷員": "Gary",
    "前端 QA 工程師": "Hannah",
    "前端工程師 A": "Ian",
    "合作夥伴經理": "Jack",
    "合規專員 Joey": "Joey",
    "安全工程師": "Kevin",
    "客戶主任": "Lisa",
    "客戶成功經理": "Mike",
    "平面設計師": "Nina",
    "後端 QA 工程師": "Oliver",
    "後端工程師 A": "Peter",
    "後端工程師 B": "Quincy",
    "技術支援 A": "Rachel",
    "數據工程師": "Steve",
    "數碼行銷員": "Tom",
    "業務發展經理 (HK)": "Uma",
    "營運經理": "Victor",
    "自動化 QA 工程師": "Wendy",
    "財務會計": "Xavier",
    "風險審計分析師": "Yolanda",
}

cur.execute("SELECT id, name FROM agents WHERE name NOT LIKE 'Chris %' ORDER BY name")
agents = cur.fetchall()

for agent_id, name in agents:
    prefix = NAME_PREFIXES.get(name, "Zara")
    chinese_name = name
    for k, v in NAME_PREFIXES.items():
        if name.startswith(k):
            chinese_name = name[len(k):].strip()
            prefix = v
            break
    new_name = f"{prefix} {chinese_name}" if chinese_name else prefix

    cur.execute("""
        UPDATE agents SET
            name = %s,
            primary_model_id = %s,
            fallback_model_id = %s,
            autonomy_policy = %s,
            max_tokens_per_day = 400000,
            max_tokens_per_month = 10000000,
            context_window_size = 500,
            max_tool_rounds = 1600,
            max_triggers = 600,
            max_llm_calls_per_day = 6000,
            heartbeat_enabled = true,
            heartbeat_interval_minutes = 30,
            heartbeat_active_hours = '01:00-23:00',
            timezone = 'Asia/Hong_Kong'
        WHERE id = %s
    """, (new_name, MODEL_ID, MODEL_ID, json.dumps(AUTONOMY_POLICY), agent_id))
    print(f"Updated: {name} -> {new_name}")

conn.commit()
cur.close()
conn.close()
print("Done!")