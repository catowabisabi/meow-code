import sqlite3, datetime, json

db = sqlite3.connect(r"F:\codebase\cato-claude\progress.db")

all_analyses = [
    ("src\\history.ts", "services/history", "JSONL文件历史管理+pending buffer+异步刷写+粘贴引用系统", "api_server/services/history/__init__.py, api_server/routes/history.py", "analyzed", "粘贴引用系统/历史undo/流式读取/tmux检测"),
    ("src\\assistant\\sessionHistory.ts", "services/history", "从Claude.ai远程API获取历史", "api_server/services/history/__init__.py", "analyzed", "架构差异: TS远程API vs Python本地SQLite"),
    ("src\\utils\\auth.ts", "utils/auth", "API Key管理+OAuth+云厂商认证+Keychain+Workspace Trust+JWT主动刷新", "api_server/services/oauth.py, api_server/routes/permissions.py", "analyzed", "CLI登录/云认证/Keychain/Trust机制"),
    ("src\\bridge\\jwtUtils.ts", "bridge/jwt", "JWT解析+主动刷新调度", "api_server/services/oauth/oauth_service.py", "analyzed", "bridge-specific JWT处理缺失"),
    ("src\\cli\\handlers\\auth.ts", "cli/auth", "OAuth登录/登出/状态查询", "api_server/services/oauth.py", "analyzed", "CLI命令端点缺失"),
    ("src\\utils\\user.ts", "utils/user", "CoreUserData+Email获取+订阅状态+Git Email", "api_server/routes/settings.py, api_server/services/remote_settings.py", "analyzed", "用户身份/订阅/Analytics整合"),
    
    ("src\\tools.ts", "tools", "41个工具注册表(含McpAuth/WebBrowser/REPL等)", "api_server/tools/", "analyzed", "McpAuthTool/WebBrowserTool/REPL/Monitor/PushNotification等14+工具缺失"),
    ("src\\commands\\init.ts", "commands/init", "NEW_INIT多阶段互动引导+worktree检测", "api_server/routes/commands.py", "analyzed", "Python只有静态模板，无互动流程"),
    ("src\\commands\\commit.ts", "commands/commit", "Git Safety Protocol+attribution处理", "api_server/routes/commands.py", "analyzed", "Python无attribution/executeShellCommandsInPrompt"),
    ("src\\commands\\review.ts", "commands/review", "Local review和ultrareview模式", "api_server/routes/commands.py", "analyzed", "Python无local-jsx UI"),
    ("src\\commands\\branch\\branch.ts", "commands/branch", "对话分支+transcript解析", "api_server/services/session_store.py", "analyzed", "Python无完整session forking"),
    ("src\\commands\\compact\\compact.ts", "commands/compact", "reactive/session memory/microcompact多种模式", "api_server/services/compact.py", "analyzed", "Python只有基本message count压缩"),
    ("src\\commands\\config\\index.ts", "commands/config", "local-jsx配置面板UI", "api_server/routes/commands.py", "analyzed", "Python无local-jsx UI"),
    ("src\\commands\\context\\index.ts", "commands/context", "上下文可视化彩色网格", "api_server/routes/commands.py", "analyzed", "Python无visual grid UI"),
    ("src\\commands\\skills\\index.ts", "commands/skills", "local-jsx技能列表UI", "api_server/routes/skills.py", "analyzed", "Python有REST API但无local-jsx UI"),
    ("src\\commands\\mcp\\index.ts", "commands/mcp", "MCP服务器管理local-jsx UI", "api_server/routes/commands.py", "analyzed", "Python有REST API但无local-jsx UI"),
    
    ("src\\utils\\file.ts", "utils/file", "路径处理+编码检测+原子写入+symlink权限", "api_server/tools/file_tools.py", "analyzed", "Python缺少编码检测/原子写入/断行符处理"),
    ("src\\utils\\git.ts", "utils/git", "完整Git操作(930行)+worktree+stash+issue状态", "api_server/services/git_service.py", "analyzed", "Python只有基本status/diff/log等"),
    ("src\\utils\\shell.ts", "utils/shell", "Shell执行框架(478行)+sandbox+task输出", "api_server/tools/bash.py", "analyzed", "Python bash.py功能较简单"),
    ("src\\utils\\config.ts", "utils/config", "复杂设定系统(1400+行)+lockfile+备份迁移", "api_server/routes/settings.py", "analyzed", "Python settings只有基本API key管理"),
    ("src\\utils\\log.ts", "utils/log", "多destination错误日志+内存缓存+持久化", "no_match", "analyzed", "Python完全无对应"),
    ("src\\utils\\env.ts", "utils/env", "平台路径+网络检测+终端检测(20+)+部署环境(30+)", "no_match", "analyzed", "Python完全无对应"),
    ("src\\utils\\crypto.ts", "utils/crypto", "Node.js密码学包装+browser环境置换", "no_match", "analyzed", "Python完全无对应"),
    ("src\\utils\\json.ts", "utils/json", "safeParseJSON(LRU)+JSONC+JSONL+尾部读取", "no_match", "analyzed", "Python完全无对应"),
    
    ("src\\hooks\\useSettings.ts", "hooks/useSettings", "AppState响应式设定Hook", "api_server/routes/settings.py", "analyzed", "Python后端无Hook机制"),
    ("src\\hooks\\useMergedTools.ts", "hooks/useMergedTools", "工具池合并去重过滤", "api_server/services/tools_service.py", "analyzed", "Python工具合并逻辑差异"),
    ("src\\hooks\\useHistorySearch.ts", "hooks/useHistorySearch", "历史搜索+键盘快捷键绑定", "api_server/services/history/", "analyzed", "前端事件驱动机制差异"),
    ("src\\hooks\\useAssistantHistory.ts", "hooks/useAssistantHistory", "助手历史分页加载", "api_server/services/history/", "analyzed", "前后端分页契约差异"),
    ("src\\hooks\\useApiKeyVerification.ts", "hooks/useApiKeyVerification", "API Key多源验证+重新验证", "api_server/services/api/claude.py", "analyzed", "Python API Key验证差异"),
    ("src\\hooks\\useIdeConnectionStatus.ts", "hooks/useIdeConnectionStatus", "MCP连接状态+IDE状态", "api_server/services/mcp_service.py", "analyzed", "MCP连接数据结构差异"),
    ("src\\hooks\\usePromptSuggestion.ts", "hooks/usePromptSuggestion", "提示建议+ telemetry日志", "api_server/services/prompt_suggestion.py", "analyzed", "telemetry字段需对齐"),
    ("src\\hooks\\useTaskListWatcher.ts", "hooks/useTaskListWatcher", "任务监听+claim提交", "api_server/tools/todo_tool.py", "analyzed", "任务字段与claim逻辑需对齐"),
    
    ("src\\services\\api\\client.ts", "services/api", "Anthropic API client多provider(Bedrock/Vertex/Foundry)", "no_match", "analyzed", "Python API server是接收端无API client"),
    ("src\\services\\compact\\compact.ts", "services/compact", "对话压缩forked agent+partial compact+hooks", "api_server/services/compact.py", "analyzed", "Python缺少forked agent/hooks/PTL retry"),
    ("src\\services\\extractMemories\\extractMemories.ts", "services/extractMemories", "记忆提取forked agent+tool权限", "api_server/services/extract_memories.py", "analyzed", "Python缺少forked agent整合"),
    ("src\\services\\lsp\\LSPClient.ts", "services/lsp", "JSON-RPC over stdio+crash处理+protocol tracing", "api_server/services/lsp/client.py", "analyzed", "Python缺少protocol tracing/crash callback"),
    ("src\\services\\mcp\\client.ts", "services/mcp", "完整MCP客户端+WS/HTTP/SSE+OAuth", "api_server/services/mcp_service.py", "analyzed", "Python缺少WebSocket/proxy/in-process server"),
    ("src\\services\\oauth\\client.ts", "services/oauth", "OAuth 2.0 PKCE+token管理+API key创建", "api_server/services/oauth.py", "analyzed", "Python缺少fetchAndStoreUserRoles/createApiKey"),
    ("src\\services\\analytics\\index.ts", "services/analytics", "事件队列+sink挂载+stripProtoFields", "api_server/services/analytics.py", "analyzed", "Python缺少stripProtoFields/PII标记"),
    ("src\\services\\tools\\toolExecution.ts", "services/tools", "完整tool执行pipeline+Zod验证+hooks+OTel", "api_server/services/tools_service.py", "analyzed", "Python只有tool usage statistics"),
    
    ("src\\bridge\\bridgeMain.ts", "bridge/main", "独立桥接进程主循环+会话管理+reconnect", "no_match", "analyzed", "Python无桥接进程主循环"),
    ("src\\bridge\\bridgeMessaging.ts", "bridge/messaging", "WebSocket消息解析+UUID echo-dedup", "api_server/routes/bridge.py", "analyzed", "Python缺少UUID dedup/control_request处理"),
    ("src\\bridge\\bridgeApi.ts", "bridge/api", "完整bridge API client+pollForWork", "no_match", "analyzed", "Python无bridge API client实现"),
    ("src\\bridge\\bridgeConfig.ts", "bridge/config", "bridge认证token和URL解析", "api_server/services/oauth/config.py", "analyzed", "bridge-specific配置缺失"),
    ("src\\bridge\\replBridge.ts", "bridge/repl", "REPL桥接核心+poll loop+reconnect", "api_server/routes/bridge.py", "analyzed", "Python缺少poll loop/reconnect logic"),
    ("src\\bridge\\sessionRunner.ts", "bridge/session", "子进程管理+NDJSON解析+stdin/stdout", "no_match", "analyzed", "Python无法spawn管理CLI进程"),
    
    ("src\\buddy\\companion.ts", "buddy/companion", "Companion gamification(18物种+稀有度+属性)", "no_match", "analyzed", "COMPLETE: Python完全无Companion系统"),
    ("src\\buddy\\types.ts", "buddy/types", "Companion类型系统(RARITIES/SPECIES/STATS)", "no_match", "analyzed", "COMPLETE: Python完全无对应"),
    ("src\\buddy\\prompt.ts", "buddy/prompt", "Companion系统提示注入", "no_match", "analyzed", "COMPLETE: Python完全无对应"),
    ("src\\coordinator\\coordinatorMode.ts", "coordinator/coordinatorMode", "多Worker协调+XML任务通知+并行执行", "api_server/services/agent_pool.py", "analyzed", "Python缺少coordinator-specific prompt/XML通知/并行协调"),
    
    ("src\\ink\\terminal.ts", "ink/terminal", "OSC 9;4进度报告+DEC同步输出+XTVERSION", "ui_only", "analyzed", "纯UI组件无Python对应"),
    ("src\\ink\\screen.ts", "ink/screen", "CharPool内存优化+ANSI渲染+宽字符处理", "ui_only", "analyzed", "纯UI组件无Python对应"),
    ("src\\ink\\renderer.ts", "ink/renderer", "React-to-terminal渲染+Yoga布局", "ui_only", "analyzed", "纯UI组件无Python对应"),
    ("src\\ink\\events\\dispatcher.ts", "ink/events", "React事件系统+capture/bubble", "ui_only", "analyzed", "纯UI组件无Python对应"),
    ("src\\components\\PromptInput\\inputPaste.ts", "components/PromptInput", "输入粘贴截断+预览", "ui_only", "analyzed", "纯UI组件无Python对应"),
    ("src\\components\\permissions\\FilePermissionDialog\\usePermissionHandler.ts", "components/permissions", "权限对话框三操作+analytics", "api_server/routes/permissions.py", "analyzed", "Python无frontend feedback/scope概念"),
]

for src_path, category, summary, api_path, status, gaps in all_analyses:
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
total = db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
print(f"Updated database: {analyzed}/{total} analyzed")

categories = db.execute("SELECT category, COUNT(*) FROM files WHERE status = 'analyzed' GROUP BY category ORDER BY COUNT(*) DESC").fetchall()
print("\nTop categories analyzed:")
for cat, count in categories[:15]:
    print(f"  {cat}: {count}")

db.close()