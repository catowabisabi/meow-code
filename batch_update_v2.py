import sqlite3, datetime

db = sqlite3.connect(r"F:\codebase\cato-claude\progress.db")

analyses = [
    ("src\\tools\\GrepTool\\GrepTool.ts", "tools/GrepTool", "文字搜尋工具核心-rg正則/glob/三種輸出模式/分頁/UNC安全", "api_server\\tools\\grep.py", "analyzed", "Python缺少UNC安全/globExclusions/WSL超時"),
    ("src\\tools\\GrepTool\\prompt.ts", "tools/GrepTool", "GrepTool提示詞", "api_server\\tools\\grep.py", "analyzed", "Python description較短"),
    ("src\\tools\\GrepTool\\UI.tsx", "tools/GrepTool", "GrepTool React UI元件", "no_match", "analyzed", "Python無React UI層"),
    ("src\\tools\\GlobTool\\GlobTool.ts", "tools/GlobTool", "檔案模式匹配工具-100結果限制/權限檢查", "api_server\\tools\\file_tools.py", "analyzed", "Python限制200非100/無truncated標誌"),
    ("src\\tools\\GlobTool\\prompt.ts", "tools/GlobTool", "GlobTool提示詞", "api_server\\tools\\file_tools.py", "analyzed", "Python description較短"),
    ("src\\tools\\GlobTool\\UI.tsx", "tools/GlobTool", "GlobTool UI", "no_match", "analyzed", "Python無React UI層"),
    ("src\\memdir\\memdir.ts", "memdir/memdir", "核心memory目錄管理-建立/truncate/build prompts/auto+team mode", "no_match", "analyzed", "需重建Bun封裝與feature gates"),
    ("src\\memdir\\findRelevantMemories.ts", "memdir/findRelevantMemories", "Sonnet選擇最相關5個記憶檔", "no_match", "analyzed", "需Sonnet API與MemoryHeader Python等價"),
    ("src\\memdir\\memoryTypes.ts", "memdir/memoryTypes", "四類型記憶系統/frontmatter模板", "no_match", "analyzed", "模板需Python版本重寫"),
    ("api_server\\agents\\tool\\execute.py", "agents/tool", "Agent生命週期管理-spawn/run/resume/fork/terminate", "python_only", "analyzed", "TS無對應server-side agent orchestration"),
    ("api_server\\agents\\tool\\loop.py", "agents/tool", "Agent loop runner (stub)", "python_only", "analyzed", "骨架實現"),
    ("api_server\\agents\\tool\\mcp.py", "agents/tool", "Per-agent MCP服務器初始化", "python_only", "analyzed", "TS無對應MCP管理"),
    ("api_server\\agents\\tool\\memory.py", "agents/tool", "Agent記憶管理-user/project/local scopes", "python_only", "analyzed", "TS無對應持久化"),
    ("api_server\\agents\\tool\\registry.py", "agents/tool", "Agent registry與built-in agent註冊", "python_only", "analyzed", "TS無對應"),
    ("api_server\\agents\\tool\\run_agent.py", "agents/tool", "核心async generator-LLM streaming/MCP/hooks/transcript", "python_only", "analyzed", "TS無對應複雜streaming"),
    ("api_server\\agents\\tool\\spawn.py", "agents/tool", "Agent spawning asyncio任務", "python_only", "analyzed", "TS無對應"),
    ("api_server\\agents\\tool\\built-in\\claude_code_guide.py", "agents/tool/built-in", "內建Claude Code指南agent", "python_only", "analyzed", "TS無對應"),
    ("api_server\\agents\\tool\\built-in\\explore.py", "agents/tool/built-in", "內建唯讀探索agent", "python_only", "analyzed", "TS無對應"),
    ("api_server\\agents\\tool\\built-in\\general_purpose.py", "agents/tool/built-in", "內建通用agent", "python_only", "analyzed", "TS無對應"),
]

for src_path, category, summary, api_path, status, gaps in analyses:
    if src_path.startswith("src\\"):
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
    elif src_path.startswith("api_server\\"):
        db.execute("""
            UPDATE python_files SET
                category = ?,
                summary = ?,
                typescript_source = ?,
                status = ?,
                analyzed_at = ?,
                notes = ?
            WHERE python_path = ?
        """, (category, summary, api_path.replace("api_server\\\\", ""), status, datetime.datetime.now().isoformat(), gaps, src_path.replace("\\", "/")))

db.commit()

ts_analyzed = db.execute("SELECT COUNT(*) FROM files WHERE status = 'analyzed'").fetchone()[0]
py_analyzed = db.execute("SELECT COUNT(*) FROM python_files WHERE status = 'analyzed'").fetchone()[0]
total = db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
py_total = db.execute("SELECT COUNT(*) FROM python_files").fetchone()[0]

print(f"Database updated!")
print(f"TypeScript: {ts_analyzed}/{total} analyzed")
print(f"Python: {py_analyzed}/{py_total} analyzed")

db.close()