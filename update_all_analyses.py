import sqlite3, datetime

db = sqlite3.connect(r"F:\codebase\cato-claude\progress.db")

analyses = [
    (r"src\history.ts", "api_server/services/history/__init__.py, api_server/routes/history.py", "analyzed",
     "TypeScript: JSONL文件存储+pending buffer+异步刷写+粘贴引用系统; Python: SQLite+FTS5+CRUD; Gap: 粘贴引用/历史undo/流式读取/tmux检测",
     datetime.datetime.now().isoformat()),
    (r"src\utils\auth.ts", "api_server/services/oauth.py, api_server/routes/permissions.py", "analyzed",
     "TypeScript: API Key管理+OAuth+云厂商认证+Keychain+Workspace Trust+JWT主动刷新; Python: 核心OAuth PKCE流程; Gap: CLI登录/云认证/Keychain/Trust机制",
     datetime.datetime.now().isoformat()),
    (r"src\utils\user.ts", "api_server/routes/settings.py, api_server/services/remote_settings.py", "analyzed",
     "TypeScript: CoreUserData+Email获取+订阅状态+Git Email+GitHub Actions metadata; Python: Settings CRUD+API凭证管理; Gap: 用户身份/订阅/Analytics整合",
     datetime.datetime.now().isoformat()),
    (r"src\coordinator\coordinatorMode.ts", "api_server/agents/loop.py, api_server/routes/agents.py", "analyzed",
     "TypeScript: Coordinator模式+多Worker协调+Companion gamification系统; Python: 核心agent loop+REST API; Gap: 多代理协调/Companion系统/内置Guide Agent",
     datetime.datetime.now().isoformat()),
    (r"src\memdir\memdir.ts", "api_server/services/memory.py, api_server/routes/memory.py", "analyzed",
     "TypeScript: Markdown+LLM语义搜索+4类型taxonomy+自动索引重建+KAIROS日志; Python: JSON CRUD+简单substring搜索; Gap: LLM搜索/类型系统/自动重建/背景提取代理",
     datetime.datetime.now().isoformat()),
    (r"src\tools.ts", "api_server/tools/", "analyzed",
     "TypeScript: 41个工具(含McpAuth/WebBrowser/REPL等); Python: 75个工具文件; Gap: McpAuthTool/WebBrowserTool/REPL/Monitor/PushNotification等14+工具",
     datetime.datetime.now().isoformat()),
]

for src_path, api_path, status, summary, analyzed_at in analyses:
    db.execute("""
      UPDATE files SET
        api_path     = ?,
        status       = ?,
        summary      = ?,
        analyzed_at  = ?,
        notes        = ?
      WHERE src_path = ?
    """, (api_path, status, summary, analyzed_at, "", src_path))

db.commit()

rows = db.execute("SELECT src_path, api_path, status FROM files WHERE status = 'analyzed'").fetchall()
print(f"Analyzed: {len(rows)}")
for r in rows:
    print(r)

completed = db.execute("SELECT COUNT(*) FROM files WHERE status = 'analyzed'").fetchone()[0]
total = db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
print(f"\nProgress: {completed} / {total} analyzed")

db.close()