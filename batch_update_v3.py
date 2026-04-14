import sqlite3, datetime

db = sqlite3.connect(r"F:\codebase\cato-claude\progress.db")

analyses = [
    ("src\\skills\\bundledSkills.ts", "skills/bundledSkills", "內建skills定義-檔案提取安全( O_NOFOLLOW/O_EXCL)", "api_server\\services\\skills\\builtin_skills.py", "analyzed", "Python無檔案提取安全"),
    ("src\\skills\\loadSkillsDir.ts", "skills/loadSkillsDir", "主要skill載入器-動態發現/frontmatter/條件skills", "api_server\\services\\skills\\loader.py + registry.py + executor.py", "analyzed", "Python缺少條件skills/動態發現/gitignore驗證"),
    ("src\\skills\\mcpSkillBuilders.ts", "skills/mcpSkillBuilders", "MCP skill builder registry", "no_match", "analyzed", "Python MCP架構不同"),
    
    ("src\\native-ts\\color-diff\\index.ts", "native-ts/color-diff", "Syntax highlighting+word diff (highlight.js)", "no_match", "analyzed", "Python無語法高亮模組"),
    ("src\\native-ts\\file-index\\index.ts", "native-ts/file-index", "Fuzzy file search-O(1) bitmap/async indexing", "no_match", "analyzed", "Python無fuzzy indexer"),
    ("src\\native-ts\\yoga-layout\\index.ts", "native-ts/yoga-layout", "Flexbox layout engine (Meta yoga)", "no_match", "analyzed", "Python無flexbox引擎"),
    
    ("src\\tasks.ts", "tasks/tasks", "Task registry工廠-聚合所有task類型", "api_server\\tools\\task_create.py", "analyzed", "Python缺少多態Task介面/kill()方法"),
    ("src\\Task.ts", "tasks/Task", "核心task定義-TaskType/TaskStatus/kill()", "api_server\\tools\\task_create.py", "analyzed", "Python Task缺乏type欄位/kill()實現"),
    ("src\\tasks\\types.ts", "tasks/types", "TaskState聯合類型+isBackgroundTask()", "api_server\\tools\\task_create.py", "analyzed", "Python無typed TaskState"),
    ("src\\tasks\\stopTask.ts", "tasks/stopTask", "共用stop邏輯-task.kill()/通知/", "api_server\\tools\\task_stop.py", "analyzed", "Python缺少task.kill()回調/Sdk事件"),
    ("src\\tasks\\LocalMainSessionTask.ts", "tasks/LocalMainSessionTask", "後台session任務-foreground/background切換", "no_match", "analyzed", "CLI特有功能-Python無對應"),
    
    ("src\\context.ts", "context/core", "Core context-git status/CLAUDE.md注入", "api_server\\prompts\\builder.py", "analyzed", "Python缺少git status整合/cache breaking"),
    ("src\\context\\stats.tsx", "context/stats", "Stats store-計數器/計時器/百分位計算", "api_server\\services\\diagnostic_tracking.py", "analyzed", "Python缺少histogram reservoir sampling"),
    ("src\\context\\notifications.tsx", "context/notifications", "通知系統-優先級隊列/超時/折疊", "no_match", "analyzed", "Python無UI通知隊列"),
    
    ("src\\migrations\\migrateAutoUpdatesToSettings.ts", "migrations/auto_updates", "遷移autoUpdates至settings.json", "no_match", "analyzed", "Python無migration系統"),
    ("src\\migrations\\migrateBypassPermissionsAcceptedToSettings.ts", "migrations/bypass_permissions", "遷移bypassPermissionsModeAccepted", "no_match", "analyzed", "Python無對應許可權遷移"),
    ("src\\migrations\\migrateFennecToOpus.ts", "migrations/fennec_to_opus", "遷移fennec模型別名至opus", "no_match", "analyzed", "Python無模型別名遷移"),
    ("src\\migrations\\migrateLegacyOpusToCurrent.ts", "migrations/legacy_opus", "遷移Opus 4.0/4.1至'opus'別名", "no_match", "analyzed", "Python無模型版本遷移"),
    ("src\\migrations\\migrateOpusToOpus1m.ts", "migrations/opus_to_opus1m", "遷移'opus'至'opus[1m]'", "no_match", "analyzed", "Python無訂閱類型判斷"),
    ("src\\migrations\\migrateReplBridgeEnabledToRemoteControlAtStartup.ts", "migrations/repl_bridge", "遷移replBridgeEnabled設定鍵", "no_match", "analyzed", "Python無REPL橋接器"),
    ("src\\migrations\\migrateSonnet1mToSonnet45.ts", "migrations/sonnet1m_to_45", "遷移'sonnet[1m]'至'sonnet-4-5'", "no_match", "analyzed", "Python無Sonnet版本遷移"),
    ("src\\migrations\\migrateSonnet45ToSonnet46.ts", "migrations/sonnet45_to_46", "遷移Sonnet 4.5至'sonnet'別名", "no_match", "analyzed", "Python無訂閱者類型判斷"),
    ("src\\migrations\\resetAutoModeOptInForDefaultOffer.ts", "migrations/auto_mode_opt_in", "重設auto mode opt-in狀態", "no_match", "analyzed", "Python無自動模式對話框"),
    ("src\\migrations\\resetProToOpusDefault.ts", "migrations/pro_to_opus_default", "重設Pro訂閱者模型預設值", "no_match", "analyzed", "Python無Pro訂閱者識別"),
    
    ("src\\vim\\motions.ts", "vim/motions", "Vim移動指令解析-hjkl/wbe/計數前輟", "no_match", "analyzed", "Python無Vim motions"),
    ("src\\vim\\operators.ts", "vim/operators", "Vim操作符-delete/change/yank/paste", "no_match", "analyzed", "Python無Vim操作符框架"),
    ("src\\vim\\textObjects.ts", "vim/textObjects", "Vim文字對象-iw/aw/引號/括號", "no_match", "analyzed", "Python無文字對象概念"),
    ("src\\vim\\transitions.ts", "vim/transitions", "Vim狀態機轉移表-11種命令狀態", "no_match", "analyzed", "Python無Vim狀態機"),
    ("src\\vim\\types.ts", "vim/types", "Vim類型定義-CommandState/Operator", "no_match", "analyzed", "Python無Vim類型系統"),
    
    ("src\\commands\\voice\\voice.ts", "voice/command", "Voice模式toggle命令", "no_match", "analyzed", "Python無/voice命令端點"),
    ("src\\hooks\\useVoice.ts", "voice/hook", "Hold-to-talk語音輸入React hook", "no_match", "analyzed", "React專有"),
    ("src\\services\\voice.ts", "voice/recording", "音訊錄製服務-cpal/SoX/arecord", "api_server\\services\\voice.py", "analyzed", "Python是stub-無native cpal FFI"),
    ("src\\services\\voiceStreamSTT.ts", "voice/stt_client", "WebSocket STT客戶端-voice_stream端點", "no_match", "analyzed", "Python無voice_stream WebSocket"),
    ("src\\services\\voiceKeyterms.ts", "voice/keyterms", "STT關鍵字優化-程式碼術語", "no_match", "analyzed", "Python無STT優化"),
    
    ("src\\outputStyles\\loadOutputStylesDir.ts", "outputStyles/load", "從markdown檔載入output styles", "api_server\\prompts\\builder.py", "analyzed", "Python無檔案式style載入"),
    ("src\\constants\\outputStyles.ts", "outputStyles/constants", "OutputStyleConfig類型+內建樣式", "api_server\\prompts\\builder.py", "analyzed", "Python無內建Explanatory/Learning樣式"),
    
    ("src\\schemas\\hooks.ts", "schemas/hooks", "Hook系統Zod schemas", "no_match", "analyzed", "Python無hook schema驗證"),
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