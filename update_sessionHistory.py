import sqlite3, datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')

db = sqlite3.connect(r"F:\codebase\cato-claude\progress.db")

db.execute("""
  UPDATE files SET
    api_path     = ?,
    status       = ?,
    summary      = ?,
    analyzed_at  = ?,
    notes        = ?
  WHERE src_path = ?
""", (
  "api_server/services/history/__init__.py",
  "analyzed",
  "TypeScript 從遠端 API 獲取歷史；Python 用本地 SQLite 存儲，功能對應但架構不同",
  datetime.datetime.now().isoformat(),
  "",
  r"src\assistant\sessionHistory.ts"
))

db.commit()

rows = db.execute("SELECT src_path, api_path, status, summary FROM files WHERE status != 'pending'").fetchall()
for r in rows:
    print(r)

completed = db.execute("SELECT COUNT(*) FROM files WHERE status != 'pending'").fetchone()[0]
total = db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
print(f"\n進度：{completed} / {total} 完成")

db.close()