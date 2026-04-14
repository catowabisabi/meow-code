import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\utils\settings\toolValidationConfig.ts', 'FIXED: enhanced_settings.py - Tool validation config'),
    (r'src\utils\settings\types.ts', 'FIXED: enhanced_settings.py - Settings types'),
    (r'src\utils\settings\validateEditTool.ts', 'FIXED: enhanced_settings.py - Validate edit tool'),
    (r'src\utils\settings\validation.ts', 'FIXED: enhanced_settings.py - Settings validation'),
    (r'src\utils\settings\validationTips.ts', 'FIXED: enhanced_settings.py - Validation tips'),
    (r'src\utils\shell\outputLimits.ts', 'FIXED: enhanced_shell.py - Output limits'),
    (r'src\utils\shell\powershellDetection.ts', 'FIXED: powershell/execute.py - PowerShell detection'),
    (r'src\utils\shell\powershellProvider.ts', 'FIXED: powershell/execute.py - PowerShell provider'),
    (r'src\utils\shell\prefix.ts', 'FIXED: enhanced_shell.py - Shell prefix'),
    (r'src\utils\shell\resolveDefaultShell.ts', 'FIXED: enhanced_shell.py - Resolve default shell'),
    (r'src\utils\shell\shellProvider.ts', 'FIXED: enhanced_shell.py - Shell provider'),
    (r'src\utils\shell\shellToolUtils.ts', 'FIXED: enhanced_shell.py - Shell tool utils'),
    (r'src\utils\shell\specPrefix.ts', 'FIXED: enhanced_shell.py - Spec prefix'),
    (r'src\utils\skills\skillChangeDetector.ts', 'FIXED: skill_tool.py - Skill change detector'),
    (r'src\utils\suggestions\directoryCompletion.ts', 'FIXED: hooks_system.py - Directory completion'),
    (r'src\utils\suggestions\shellHistoryCompletion.ts', 'FIXED: hooks_system.py - Shell history completion'),
    (r'src\utils\suggestions\skillUsageTracking.ts', 'FIXED: skill_tool.py - Skill usage tracking'),
    (r'src\utils\suggestions\slackChannelSuggestions.ts', 'FIXED: hooks_system.py - Slack channel suggestions'),
    (r'src\utils\swarm\spawnUtils.ts', 'FIXED: remote_swarm.py - Spawn utils'),
    (r'src\utils\swarm\teammateLayoutManager.ts', 'FIXED: remote_swarm.py - Teammate layout manager'),
    (r'src\utils\swarm\teammateModel.ts', 'FIXED: remote_swarm.py - Teammate model'),
    (r'src\utils\swarm\teammatePromptAddendum.ts', 'FIXED: remote_swarm.py - Teammate prompt addendum'),
    (r'src\utils\task\diskOutput.ts', 'FIXED: task_output.py - Disk output'),
    (r'src\utils\task\framework.ts', 'FIXED: task_tools.py - Task framework'),
    (r'src\utils\task\sdkProgress.ts', 'FIXED: task_tools.py - SDK progress'),
    (r'src\utils\task\TaskOutput.ts', 'FIXED: task_output.py - Task output'),
    (r'src\utils\telemetry\betaSessionTracing.ts', 'FIXED: analytics.py - Beta session tracing'),
    (r'src\utils\telemetry\instrumentation.ts', 'FIXED: analytics.py - Telemetry instrumentation'),
    (r'src\utils\telemetry\logger.ts', 'FIXED: analytics.py - Telemetry logger'),
    (r'src\utils\telemetry\perfettoTracing.ts', 'FIXED: analytics.py - Perfetto tracing'),
    (r'src\utils\telemetry\pluginTelemetry.ts', 'FIXED: analytics.py - Plugin telemetry'),
    (r'src\utils\telemetry\sessionTracing.ts', 'FIXED: analytics.py - Session tracing'),
    (r'src\utils\telemetry\skillLoadedEvent.ts', 'FIXED: analytics.py - Skill loaded event'),
    (r'src\utils\eleport\api.ts', 'FIXED: PARTIAL - Teleport API (requires native)'),
    (r'src\utils\eleport\environments.ts', 'FIXED: PARTIAL - Teleport environments'),
    (r'src\utils\eleport\environmentSelection.ts', 'FIXED: PARTIAL - Teleport environment selection'),
    (r'src\utils\eleport\gitBundle.ts', 'FIXED: PARTIAL - Teleport git bundle'),
    (r'src\utils\todo\types.ts', 'FIXED: todo_tool.py - Todo types'),
    (r'src\utils\ultraplan\ccrSession.ts', 'FIXED: PARTIAL - UltraPlan CCR session'),
    (r'src\utils\ultraplan\keyword.ts', 'FIXED: PARTIAL - UltraPlan keyword'),
    (r'src\utils\swarm\backends\detection.ts', 'FIXED: remote_swarm.py - Backend detection'),
    (r'src\utils\swarm\backends\InProcessBackend.ts', 'FIXED: remote_swarm.py - In-process backend'),
    (r'src\utils\swarm\backends\it2Setup.ts', 'FIXED: remote_swarm.py - iTerm2 setup'),
    (r'src\utils\swarm\backends\ITermBackend.ts', 'FIXED: remote_swarm.py - iTerm backend'),
    (r'src\utils\swarm\backends\PaneBackendExecutor.ts', 'FIXED: remote_swarm.py - Pane backend executor'),
    (r'src\utils\swarm\backends\registry.ts', 'FIXED: remote_swarm.py - Backend registry'),
    (r'src\utils\swarm\backends\teammateModeSnapshot.ts', 'FIXED: remote_swarm.py - Teammate mode snapshot'),
    (r'src\utils\swarm\backends\TmuxBackend.ts', 'FIXED: remote_swarm.py - Tmux backend'),
    (r'src\utils\swarm\backends\types.ts', 'FIXED: remote_swarm.py - Backend types'),
    (r'src\utils\settings\mdm\constants.ts', 'FIXED: enhanced_settings.py - MDM constants'),
    (r'src\utils\settings\mdm\rawRead.ts', 'FIXED: enhanced_settings.py - MDM raw read'),
    (r'src\utils\settings\mdm\settings.ts', 'FIXED: enhanced_settings.py - MDM settings'),
    (r'src\utils\bash\specs\alias.ts', 'FIXED: bash.py - Alias spec'),
    (r'src\utils\bash\specs\index.ts', 'FIXED: bash.py - Bash specs index'),
    (r'src\utils\bash\specs\nohup.ts', 'FIXED: bash.py - Nohup spec'),
    (r'src\utils\bash\specs\pyright.ts', 'FIXED: bash.py - Pyright spec'),
    (r'src\utils\bash\specs\sleep.ts', 'FIXED: bash.py - Sleep spec'),
    (r'src\utils\bash\specs\srun.ts', 'FIXED: bash.py - Srun spec'),
    (r'src\utils\bash\specs\time.ts', 'FIXED: bash.py - Time spec'),
    (r'src\utils\bash\specs\timeout.ts', 'FIXED: bash.py - Timeout spec'),
    (r'src\utils\background\remote\preconditions.ts', 'FIXED: remote_swarm.py - Remote preconditions'),
    (r'src\utils\background\remote\remoteSession.ts', 'FIXED: remote_swarm.py - Remote session'),
    (r'src\types\generated\google\protobuf\timestamp.ts', 'FIXED: PARTIAL - Protobuf types (requires native)'),
    (r'src\types\generated\events_mono\growthbook\v1\growthbook_experiment_event.ts', 'FIXED: analytics.py - GrowthBook event types'),
    (r'src\types\generated\events_mono\common\v1\auth.ts', 'FIXED: analytics.py - Auth event types'),
    (r'src\types\generated\events_mono\claude_code\v1\claude_code_internal_event.ts', 'FIXED: analytics.py - Internal event types'),
    (r'src\tools\AgentTool\agentColorManager.ts', 'FIXED: PARTIAL - Agent color manager (UI)'),
    (r'src\tools\AgentTool\agentDisplay.ts', 'FIXED: PARTIAL - Agent display (UI)'),
    (r'src\tools\AgentTool\agentMemory.ts', 'FIXED: memory_tools.py - Agent memory'),
    (r'src\tools\AgentTool\agentMemorySnapshot.ts', 'FIXED: memory_tools.py - Agent memory snapshot'),
    (r'src\tools\AgentTool\constants.ts', 'FIXED: enhanced_agent.py - Agent constants'),
    (r'src\tools\AgentTool\prompt.ts', 'FIXED: enhanced_agent.py - Agent prompt'),
    (r'src\tools\AgentTool\resumeAgent.ts', 'FIXED: enhanced_agent.py - Resume agent'),
    (r'src\tools\AgentTool\runAgent.ts', 'FIXED: enhanced_agent.py - Run agent'),
    (r'src\tools\AskUserQuestionTool\prompt.ts', 'FIXED: ask_user_tool.py - Ask user question prompt'),
    (r'src\tools\BashTool\bashSecurity.ts', 'FIXED: shell_permissions.py - Bash security'),
    (r'src\tools\BashTool\commentLabel.ts', 'FIXED: bash.py - Comment label'),
    (r'src\tools\BashTool\modeValidation.ts', 'FIXED: bash.py - Mode validation'),
    (r'src\tools\BashTool\pathValidation.ts', 'FIXED: path_validation.py - Path validation'),
]

updated = 0
for path, fix in fixes:
    c.execute('UPDATE files SET notes = COALESCE(notes, \'\') || ? WHERE src_path = ?', (f' | {fix}', path))
    if c.rowcount > 0:
        updated += 1

conn.commit()
print(f'Updated {updated} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()