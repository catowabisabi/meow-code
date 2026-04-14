import sqlite3, datetime

db = sqlite3.connect(r"F:\codebase\cato-claude\progress.db")

analyses = [
    ("src\\assistant\\sessionHistory.ts", "assistant/sessionHistory", "遠程 API 歷史獲取-OAuth/Beta header/before_id分頁", "api_server\\services\\history\\__init__.py", "analyzed", "TS遠程API vs Python本地SQLite; 無anchor_to_latest"),
    
    ("src\\server\\createDirectConnectSession.ts", "server/direct-connect-session", "直接連接session建立-POST /sessions", "api_server\\services\\mcp\\server.py", "analyzed", "Python缺少DirectConnectConfig錯誤類型"),
    ("src\\server\\directConnectManager.ts", "server/direct-connect-manager", "直接連接生命週期管理", "api_server\\lsp\\server_manager.py", "analyzed", "TypeScript/Node vs Python環境差異"),
    
    ("src\\components\\permissions\\FilePermissionDialog\\FilePermissionDialog.tsx", "components/permissions", "檔案權限對話框-IDE diff/符號鏈接警告", "api_server\\routes\\permissions.py", "analyzed", "TS豐富UI vs Python僅REST端點"),
    ("src\\components\\PromptInput\\PromptInput.tsx", "components", "主要prompt輸入-建議/歷史/slash commands", "no_match", "analyzed", "純前端TUI組件-Python無對應"),
    
    ("src\\constants\\apiLimits.ts", "constants/apiLimits", "API限制-圖片5MB/PDF100頁/媒體100項", "api_server\\services\\policy_limits\\limits.py", "analyzed", "Python有對應limits"),
    ("src\\constants\\betas.ts", "constants/betas", "Beta功能header管理", "no_match", "analyzed", "Python無Beta header"),
    ("src\\constants\\common.ts", "constants/common", "日期時間輔助函式", "no_match", "analyzed", "Python無對等模組"),
    ("src\\constants\\errorIds.ts", "constants/errorIds", "錯誤ID追蹤系統", "no_match", "analyzed", "Python無混淆錯誤ID"),
    ("src\\constants\\keys.ts", "constants/keys", "GrowthBook SDK金鑰", "no_match", "analyzed", "Python GrowthBook整合未知"),
    ("src\\constants\\oauth.ts", "constants/oauth", "OAuth設定-prod/staging/local配置", "api_server\\services\\oauth\\", "analyzed", "Python有OAuth服務但常量配置方式不同"),
    ("src\\constants\\outputStyles.ts", "constants/outputStyles", "輸出風格配置-Explanatory/Learning", "no_match", "analyzed", "CLI特有功能"),
    ("src\\constants\\system.ts", "constants/system", "CLI系統提示前綴/attribution header", "no_match", "analyzed", "Python無CLI系統提示管理"),
    ("src\\constants\\toolLimits.ts", "constants/toolLimits", "工具結果大小限制-50K/100K/200K", "no_match", "analyzed", "Python無工具限制常量"),
    ("src\\constants\\tools.ts", "constants/tools", "工具權限常量-ALL_AGENT_DISALLOWED", "no_match", "analyzed", "Python工具registry權限定義方式不同"),
    
    ("src\\state\\store.ts", "state/store", "輕量級狀態store工廠-getState/setState/subscribe", "no_match", "analyzed", "Python無reactive store模式"),
    ("src\\state\\selectors.ts", "state/selectors", "AppState選擇器-getViewedTeammateTask", "no_match", "analyzed", "Python無selector模式"),
    ("src\\state\\AppStateStore.ts", "state/AppStateStore", "主要應用狀態容器-500+行涵蓋所有屬性", "api_server\\services\\session_store.py", "analyzed", "Python狀態分散在各服務而非統一容器"),
    
    ("src\\upstreamproxy\\upstreamproxy.ts", "upstreamproxy/main", "Container端上游代理-Token讀取/CA證書/MITM", "no_match", "analyzed", "COMPLETE: Python無MITM代理注入"),
    ("src\\upstreamproxy\\relay.ts", "upstreamproxy/relay", "WebSocket relay-CONNECT隧道/protobuf編碼", "no_match", "analyzed", "COMPLETE: Python無CONNECT隧道"),
    
    ("src\\query\\config.ts", "query/config", "查詢配置快照-Runtime gates/Statsig", "no_match", "analyzed", "Python無查詢配置快照"),
    ("src\\query\\deps.ts", "query/deps", "查詢依賴注入工廠", "no_match", "analyzed", "Python直接導入無DI機制"),
    ("src\\query\\stopHooks.ts", "query/stopHooks", "查詢停止條件-Stop/TeammateIdle/TaskCompleted", "no_match", "analyzed", "Python無stop hooks"),
    ("src\\query\\tokenBudget.ts", "query/tokenBudget", "Token預算追蹤-continuationCount", "api_server\\services\\api\\claude.py", "analyzed", "Python預算追蹤分散在API層"),
    
    ("src\\plugins\\builtinPlugins.ts", "plugins/builtinPlugins", "內建插件註冊管理", "api_server\\services\\plugins\\config.py", "analyzed", "TypeScript只有scaffold-Python有完整生命週期"),
    ("src\\plugins\\bundled\\index.ts", "plugins/bundled", "捆綁插件初始化-幾乎空殼", "no_match", "analyzed", "空檔案"),
    
    ("src\\entrypoints\\cli.tsx", "entrypoints/cli", "CLI入口-命令路由/version check/daemon", "api_server\\main.py", "analyzed", "Python無CLI路由/fast-path/daemon workers"),
    ("src\\entrypoints\\init.ts", "entrypoints/init", "初始化入口-OAuth/telemetry/mTLS/proxy", "api_server\\main.py lifespan", "analyzed", "Python缺少telemetry/OAuth/policy limits"),
    ("src\\entrypoints\\mcp.ts", "entrypoints/mcp", "MCP服務器-StdioServerTransport/ListTools", "api_server\\agents\\tool\\mcp.py", "analyzed", "Python MCP只是工具而非服務傳輸"),
    ("src\\entrypoints\\agentSdkTypes.ts", "entrypoints/agentSdkTypes", "Agent SDK公共API-types/query/session", "no_match", "analyzed", "COMPLETE: Python無SDK"),
    
    ("src\\bootstrap\\state.ts", "bootstrap/state", "全局狀態管理-1767行", "no_match", "analyzed", "TypeScript特有狀態管理模式"),
]

for src_path, category, summary, api_path, status, gaps in analyses:
    db.execute("""
        UPDATE files SET
            category = ?,
            summary = ?,
            api_path = ?,
            status = ?,
            analyzed_at = ?,
            notes = ?
        WHERE src_path = ?
    """, (category, summary, api_path, status, datetime.datetime.now().isoformat(), gaps, src_path))

db.commit()

analyzed = db.execute("SELECT COUNT(*) FROM files WHERE status = 'analyzed'").fetchone()[0]
pending = db.execute("SELECT COUNT(*) FROM files WHERE status = 'pending'").fetchone()[0]
total = db.execute("SELECT COUNT(*) FROM files").fetchone()[0]

print(f"Database updated!")
print(f"Analyzed: {analyzed}/{total} ({analyzed*100//total}%)")
print(f"Pending: {pending}")

by_category = db.execute("SELECT category, COUNT(*) FROM files WHERE status = 'analyzed' GROUP BY category ORDER BY COUNT(*) DESC LIMIT 15").fetchall()
print("\nTop categories analyzed:")
for cat, cnt in by_category:
    print(f"  {cat}: {cnt}")

db.close()