import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('F:/codebase/cato-claude/test_records.db')
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS api_test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_date TEXT,
        total INTEGER,
        passed INTEGER,
        failed INTEGER,
        pass_rate TEXT,
        failed_endpoints TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")

with open('F:/codebase/cato-claude/api_server/test_results.json') as f:
    data = json.load(f)

failed = [r for r in data['results'] if not r['success']]
failed_list = [(r['method'], r['path'], r['status'], r['error']) for r in failed]

cur.execute("""
    INSERT INTO api_test_results (test_date, total, passed, failed, pass_rate, failed_endpoints)
    VALUES (?, ?, ?, ?, ?, ?)
""", (
    datetime.now().isoformat(),
    data['total'],
    data['passed'],
    data['failed'],
    data['pass_rate'],
    json.dumps(failed_list, ensure_ascii=False)
))

conn.commit()
conn.close()
print(f"Updated test_records.db with API test results: {data['passed']}/{data['total']} passed ({data['pass_rate']})")