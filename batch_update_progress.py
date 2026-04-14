import sqlite3, datetime

db = sqlite3.connect(r"F:\codebase\cato-claude\progress.db")

analyses = [
    ("src\\commands\\exit\\index.ts", "commands/exit", "退出命令", "api_server/routes/commands.py", "analyzed", "TS local-jsx vs Python REST"),
    ("src\\commands\\resume\\index.ts", "commands/resume", "继续对话命令", "api_server/routes/commands.py", "analyzed", "TS search term vs Python session_id only"),
    ("src\\commands\\rewind\\rewind.ts", "commands/rewind", "消息选择器UI", "api_server/routes/commands.py", "analyzed", "TS UI selector vs Python mechanical delete"),
    ("src\\commands\\plan\\index.ts", "commands/plan", "计划模式命令", "api_server/routes/commands.py + agents/tool/built-in/plan.py", "analyzed", "TS local-jsx UI vs Python REST"),
    ("src\\commands\\privacy-settings\\index.ts", "commands/privacy-settings", "隐私设定", "api_server/routes/privacy_settings.py", "analyzed", "Consumer gating差异"),
    ("src\\commands\\release-notes\\release-notes.ts", "commands/release-notes", "版本资讯获取", "no_match", "analyzed", "COMPLETE GAP: Python无对应"),
    ("src\\commands\\vim\\vim.ts", "commands/vim", "Vim模式切换", "api_server/routes/commands.py", "analyzed", "TS analytics vs Python basic toggle"),
    ("src\\commands\\add-dir\\index.ts", "commands/add-dir", "新增目录命令", "api_server/routes/commands.py", "analyzed", "TS local-jsx vs Python registry only"),
    ("src\\commands\\btw\\index.ts", "commands/btw", "顺便说命令", "api_server/routes/commands.py", "analyzed", "TS local-jsx UI vs Python type"),

    ("src\\services\\lsp\\LSPServerManager.ts", "services/lsp", "LSP服务器生命周期管理", "api_server/lsp/server_manager.py", "analyzed", "功能完整，约85% parity"),
    ("src\\services\\lsp\\passiveFeedback.ts", "services/lsp", "LSP诊断处理", "api_server/services/lsp/passive_feedback.py", "analyzed", "Python版本功能完整"),
    ("src\\services\\mcp\\auth.ts", "services/mcp", "MCP OAuth认证+XAA+step-up", "api_server/services/mcp/auth.py + oauth/", "analyzed", "Python缺少XAA/step-up auth/ClaudeAuthProvider"),
    ("src\\services\\mcp\\config.ts", "services/mcp", "MCP配置管理+scope+dedup", "api_server/services/mcp/config.py", "analyzed", "Python功能完整，约85%"),
    ("src\\services\\mcp\\oauthPort.ts", "services/mcp", "OAuth redirect port helper", "api_server/services/mcp/oauth_port.py", "analyzed", "Python版本功能完整"),
    ("src\\services\\mcp\\utils.ts", "services/mcp", "MCP工具函数", "api_server/services/mcp/config.py", "analyzed", "Python缺少工具过滤/excludeStaleClient"),
    ("src\\services\\plugins\\PluginInstallationManager.ts", "services/plugins", "背景plugin安装管理器", "api_server/services/plugins/operations.py", "analyzed", "Python严重简化，无reconcileMarketplaces"),
    ("src\\services\\plugins\\pluginOperations.ts", "services/plugins", "Plugin CRUD操作", "api_server/services/plugins/operations.py", "analyzed", "Python功能约60%，缺少marketplace整合"),
    ("src\\services\\notifier.ts", "services", "系统通知(多channel)", "api_server/services/notifier.py", "analyzed", "Python缺少终端整合/notification hooks"),
    ("src\\services\\rateLimitMessages.ts", "services", "Rate limit消息生成", "api_server/services/rate_limit/rate_limit_handler.py", "analyzed", "Python消息格式化逻辑差异"),

    ("src\\tools\\AgentTool\\runAgent.ts", "tools/agent", "Agent执行引擎(977行)", "api_server/agents/tool/run_agent.py", "analyzed", "Python是stub，缺少MCP/hooks/transcript"),
    ("src\\tools\\AgentTool\\forkSubagent.ts", "tools/agent", "Fork subagent功能", "api_server/services/auto_dream/fork_agent.py", "analyzed", "Python缺少fork boilerplate injection"),
    ("src\\tools\\AgentTool\\built-in\\generalPurposeAgent.ts", "tools/agent/built-in", "通用研究agent", "api_server/agents/tool/built-in/explore.py", "analyzed", "Python是separate Explore agent"),
    ("src\\tools\\AgentTool\\built-in\\planAgent.ts", "tools/agent/built-in", "Read-only计划agent", "api_server/agents/tool/built-in/plan.py", "analyzed", "Python版本功能完整"),
    ("src\\tools\\AgentTool\\built-in\\verificationAgent.ts", "tools/agent/built-in", "验证agent", "api_server/agents/tool/built-in/verification.py", "analyzed", "Python版本功能完整"),
    ("src\\tools\\BashTool\\bashCommandHelpers.ts", "tools/bash", "Bash命令解析+权限检查", "api_server/tools/powershell_tool.py", "analyzed", "Python是PowerShell-focused，缺少tree-sitter"),
    ("src\\tools\\BashTool\\pathValidation.ts", "tools/bash", "路径验证(1307行)", "api_server/tools/path_validation.py", "analyzed", "Python是PowerShell-specific，缺少wrapper stripping"),
    ("src\\tools\\BashTool\\readOnlyValidation.ts", "tools/bash", "只读命令allowlist(1558+行)", "api_server/tools/read_only_validation.py", "analyzed", "Python是PowerShell-specific，缺少bash regex"),
    ("src\\tools\\FileReadTool\\imageProcessor.ts", "tools/fileread", "Sharp图像处理", "no_match", "analyzed", "Python无图像处理"),
    ("src\\tools\\FileReadTool\\limits.ts", "tools/fileread", "文件读取限制+GrowthBook", "no_match", "analyzed", "Python无GrowthBook限制"),

    ("src\\utils\\bash\\commands.ts", "utils/bash", "Bash命令处理+security", "api_server/tools/bash.py + sandbox/bash_security.py", "analyzed", "Python缺少tree-sitter/AI prefix detection"),
    ("src\\utils\\bash\\parser.ts", "utils/bash", "tree-sitter bash解析器wrapper", "no_match", "analyzed", "CRITICAL: Python无tree-sitter解析"),
    ("src\\utils\\bash\\shellCompletion.ts", "utils/bash", "Shell自动补全", "no_match", "analyzed", "Python无shell completion生成"),
    ("src\\utils\\bash\\treeSitterAnalysis.ts", "utils/bash", "tree-sitter AST安全分析", "api_server/services/sandbox/bash_security.py", "analyzed", "Python用regex，缺少AST精确度"),
    ("src\\utils\\model\\model.ts", "utils/model", "模型选择+aliases+defaults", "api_server/adapters/router.py + anthropic.py", "analyzed", "Python缺少alias系统/subscription defaults"),
    ("src\\utils\\model\\configs.ts", "utils/model", "模型配置(11种模型)", "api_server/adapters/anthropic.py + base.py", "analyzed", "Python缺少统一配置registry"),
    ("src\\utils\\model\\providers.ts", "utils/model", "API provider检测", "api_server/adapters/router.py", "analyzed", "Python用adapter模式而非env检测"),
    ("src\\utils\\model\\bedrock.ts", "utils/model", "AWS Bedrock集成", "no_match", "analyzed", "Python无Bedrock支持"),
    ("src\\utils\\settings\\settings.ts", "utils/settings", "多源设置管理(1019行)", "api_server/db/settings_db.py + routes/settings.py", "analyzed", "Python缺少multi-source cascade/MDM"),
    ("src\\utils\\settings\\validation.ts", "utils/settings", "Zod设置验证", "api_server/db/settings_db.py", "analyzed", "Python缺少schema验证"),

    ("src\\state\\store.ts", "state/store", "响应式状态存储", "no_match", "analyzed", "Python无响应式store模式"),
    ("src\\state\\selectors.ts", "state/selectors", "AppState选择器", "no_match", "analyzed", "Python无selector模式"),
    ("src\\state\\AppStateStore.ts", "state/AppStateStore", "统一AppState容器", "api_server/services/session_store.py + plugins/manager.py", "analyzed", "Python拆分为多个独立service"),
    ("src\\remote\\RemoteSessionManager.ts", "remote/RemoteSessionManager", "远程CCR session管理", "api_server/ws/chat.py + bridge_ws.py", "analyzed", "Python缺少专门RemoteSessionManager"),
    ("src\\remote\\SessionsWebSocket.ts", "remote/SessionsWebSocket", "WebSocket客户端+重连", "api_server/ws/chat.py", "analyzed", "Python缺少reconnection逻辑"),
    ("src\\remote\\sdkMessageAdapter.ts", "remote/sdkMessageAdapter", "CCR SDK消息格式转换", "no_match", "analyzed", "Python无SDK message adapter"),
    ("src\\server\\directConnectManager.ts", "server/directConnectManager", "直接连接WebSocket管理", "api_server/ws/chat.py", "analyzed", "Python缺少direct connect protocol"),
    ("src\\plugins\\builtinPlugins.ts", "plugins/builtinPlugins", "内置plugin注册表", "api_server/services/plugins/manager.py", "analyzed", "Python缺少built-in vs marketplace区分"),
    ("src\\keybindings\\defaultBindings.ts", "keybindings/defaultBindings", "CLI键盘快捷键定义", "no_match", "analyzed", "Python无keybinding系统"),

    ("src\\types\\hooks.ts", "types/hooks", "Hook系统Zod schema", "api_server/services/tools/hooks.py", "analyzed", "Python缺少事件类型枚举/Zod验证"),
    ("src\\types\\permissions.ts", "types/permissions", "完整权限类型系统", "api_server/routes/permissions.py", "analyzed", "Python缺少多层权限/分类器整合"),
    ("src\\types\\plugin.ts", "types/plugin", "Plugin类型(27种错误)", "api_server/services/plugins/manager.py", "analyzed", "Python缺少详细错误类型系统"),
    ("src\\types\\generated\\events_mono\\claude_code\\v1\\claude_code_internal_event.ts", "types/generated", "Protobuf事件类型", "no_match", "analyzed", "Python无protobuf产生类型"),
    ("src\\constants\\keys.ts", "constants/keys", "GrowthBook SDK密钥", "no_match", "analyzed", "Python无GrowthBook集成"),
    ("src\\constants\\oauth.ts", "constants/oauth", "OAuth配置+scopes", "api_server/services/oauth/", "analyzed", "Python缺少MCP_PROXY/FedStart支持"),
    ("src\\constants\\prompts.ts", "constants/prompts", "系统提示词构建(动态sections)", "api_server/prompts/builder.py", "analyzed", "Python缺少动态section/GrowthBook"),
    ("src\\constants\\system.ts", "constants/system", "系统提示前缀+attribution header", "api_server/prompts/builder.py", "analyzed", "Python无attribution header机制"),
    ("src\\constants\\tools.ts", "constants/tools", "工具权限常量(4种模式)", "api_server/agents/tool/types.py", "analyzed", "Python缺少清晰权限分组"),

    ("src\\utils\\telemetry\\events.ts", "utils/telemetry", "OpenTelemetry事件发射", "api_server/services/internal_logging.py", "analyzed", "Python缺少事件属性/prompt ID追踪"),
    ("src\\utils\\telemetry\\logger.ts", "utils/telemetry", "OTEL诊断logger", "api_server/services/internal_logging.py", "analyzed", "Python缺少DiagLogger完整实现"),
    ("src\\utils\\telemetry\\instrumentation.ts", "utils/telemetry", "OTEL初始化+exporters", "api_server/services/internal_logging.py", "analyzed", "Python无OTLP/Prometheus/BigQuery"),
    ("src\\utils\\swarm\\spawnUtils.ts", "utils/swarm", "队友进程生成工具", "api_server/agents/tool/spawn.py", "analyzed", "Python缺少CLI flag继承/env传递"),
    ("src\\utils\\swarm\\teammateInit.ts", "utils/swarm", "队友初始化hooks", "api_server/agents/teammate/executor.py", "analyzed", "Python缺少Stop钩子/idle通知"),
    ("src\\utils\\swarm\\backends\\TmuxBackend.ts", "utils/swarm/backends", "Tmux后端实现", "api_server/agents/teammate/tmux_backend.py", "analyzed", "Python功能基本对应"),
    ("src\\utils\\suggestions\\commandSuggestions.ts", "utils/suggestions", "Fuse.js命令建议", "no_match", "analyzed", "Python无slash command建议"),
    ("src\\utils\\hooks\\hooksConfigManager.ts", "utils/hooks", "Hook配置管理器(26+事件)", "api_server/routes/hooks.py", "analyzed", "Python钩子类型较少"),
    ("src\\utils\\hooks\\sessionHooks.ts", "utils/hooks", "会话范围临时hook", "api_server/routes/hooks.py", "analyzed", "Python缺少FunctionHook/timeout"),
    ("src\\utils\\sandbox\\sandbox-adapter.ts", "utils/sandbox", "Sandbox-runtime桥接", "api_server/sandbox/sandboxed_shell.py + adapters/base.py", "analyzed", "Python缺少路径解析/worktree检测"),
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

by_category = db.execute("SELECT category, COUNT(*) FROM files WHERE status = 'analyzed' GROUP BY category ORDER BY COUNT(*) DESC LIMIT 20").fetchall()
print("\nTop categories analyzed:")
for cat, cnt in by_category:
    print(f"  {cat}: {cnt}")

db.close()