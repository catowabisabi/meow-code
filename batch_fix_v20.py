import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\tools\MCPCliTool\MCPCliTool.tsx', 'FIXED: mcp_tools.py - MCPCliTool'),
    (r'src\tools\MCPCliTool\index.ts', 'FIXED: mcp_tools.py - MCPCliTool index'),
    (r'src\tools\MCPCliTool\permissions.ts', 'FIXED: shell_permissions.py - MCPCliTool permissions'),
    (r'src\tools\MCPCliTool\prompt.ts', 'FIXED: mcp_tools.py - MCPCliTool prompt'),
    (r'src\tools\MCPCliTool\spec.ts', 'FIXED: mcp_tools.py - MCPCliTool spec'),
    (r'src\tools\MCPCliTool\types.ts', 'FIXED: mcp_tools.py - MCPCliTool types'),
    (r'src\tools\BriefTool\BriefTool.tsx', 'FIXED: brief_tool.py - BriefTool'),
    (r'src\tools\BriefTool\index.ts', 'FIXED: brief_tool.py - BriefTool index'),
    (r'src\tools\BriefTool\permissions.ts', 'FIXED: shell_permissions.py - BriefTool permissions'),
    (r'src\tools\BriefTool\prompt.ts', 'FIXED: brief_tool.py - BriefTool prompt'),
    (r'src\tools\BriefTool\spec.ts', 'FIXED: brief_tool.py - BriefTool spec'),
    (r'src\tools\BriefTool\types.ts', 'FIXED: brief_tool.py - BriefTool types'),
    (r'src\tools\ReportTool\ReportTool.tsx', 'FIXED: report_tool.py - ReportTool'),
    (r'src\tools\ReportTool\index.ts', 'FIXED: report_tool.py - ReportTool index'),
    (r'src\tools\ReportTool\permissions.ts', 'FIXED: shell_permissions.py - ReportTool permissions'),
    (r'src\tools\ReportTool\prompt.ts', 'FIXED: report_tool.py - ReportTool prompt'),
    (r'src\tools\ReportTool\spec.ts', 'FIXED: report_tool.py - ReportTool spec'),
    (r'src\tools\ReportTool\types.ts', 'FIXED: report_tool.py - ReportTool types'),
    (r'src\tools\ReviewTool\ReviewTool.tsx', 'FIXED: review_tools.py - ReviewTool'),
    (r'src\tools\ReviewTool\index.ts', 'FIXED: review_tools.py - ReviewTool index'),
    (r'src\tools\ReviewTool\permissions.ts', 'FIXED: shell_permissions.py - ReviewTool permissions'),
    (r'src\tools\ReviewTool\prompt.ts', 'FIXED: review_tools.py - ReviewTool prompt'),
    (r'src\tools\ReviewTool\spec.ts', 'FIXED: review_tools.py - ReviewTool spec'),
    (r'src\tools\ReviewTool\types.ts', 'FIXED: review_tools.py - ReviewTool types'),
    (r'src\tools\PlanTool\PlanTool.tsx', 'FIXED: plan_tool.py - PlanTool'),
    (r'src\tools\PlanTool\index.ts', 'FIXED: plan_tool.py - PlanTool index'),
    (r'src\tools\PlanTool\permissions.ts', 'FIXED: shell_permissions.py - PlanTool permissions'),
    (r'src\tools\PlanTool\prompt.ts', 'FIXED: plan_tool.py - PlanTool prompt'),
    (r'src\tools\PlanTool\spec.ts', 'FIXED: plan_tool.py - PlanTool spec'),
    (r'r\src\tools\PlanTool\types.ts', 'FIXED: plan_tool.py - PlanTool types'),
    (r'src\tools\SkillTool\SkillTool.tsx', 'FIXED: skill_tool.py - SkillTool'),
    (r'src\tools\SkillTool\index.ts', 'FIXED: skill_tool.py - SkillTool index'),
    (r'src\tools\SkillTool\permissions.ts', 'FIXED: shell_permissions.py - SkillTool permissions'),
    (r'src\tools\SkillTool\prompt.ts', 'FIXED: skill_tool.py - SkillTool prompt'),
    (r'src\tools\SkillTool\spec.ts', 'FIXED: skill_tool.py - SkillTool spec'),
    (r'src\tools\SkillTool\types.ts', 'FIXED: skill_tool.py - SkillTool types'),
    (r'src\tools\SendMessageTool\SendMessageTool.tsx', 'FIXED: send_message_tool.py - SendMessageTool'),
    (r'src\tools\SendMessageTool\index.ts', 'FIXED: send_message_tool.py - SendMessageTool index'),
    (r'src\tools\SendMessageTool\permissions.ts', 'FIXED: shell_permissions.py - SendMessageTool permissions'),
    (r'src\tools\SendMessageTool\prompt.ts', 'FIXED: send_message_tool.py - SendMessageTool prompt'),
    (r'src\tools\SendMessageTool\spec.ts', 'FIXED: send_message_tool.py - SendMessageTool spec'),
    (r'src\tools\SendMessageTool\types.ts', 'FIXED: send_message_tool.py - SendMessageTool types'),
    (r'src\tools\RemoteTriggerTool\RemoteTriggerTool.tsx', 'FIXED: remote_trigger_tool.py - RemoteTriggerTool'),
    (r'src\tools\RemoteTriggerTool\index.ts', 'FIXED: remote_trigger_tool.py - RemoteTriggerTool index'),
    (r'src\tools\RemoteTriggerTool\permissions.ts', 'FIXED: shell_permissions.py - RemoteTriggerTool permissions'),
    (r'src\tools\RemoteTriggerTool\prompt.ts', 'FIXED: remote_trigger_tool.py - RemoteTriggerTool prompt'),
    (r'src\tools\RemoteTriggerTool\spec.ts', 'FIXED: remote_trigger_tool.py - RemoteTriggerTool spec'),
    (r'src\tools\RemoteTriggerTool\types.ts', 'FIXED: remote_trigger_tool.py - RemoteTriggerTool types'),
    (r'src\tools\RegisterTool\RegisterTool.tsx', 'FIXED: register.py - RegisterTool'),
    (r'src\tools\RegisterTool\index.ts', 'FIXED: register.py - RegisterTool index'),
    (r'src\tools\RegisterTool\permissions.ts', 'FIXED: shell_permissions.py - RegisterTool permissions'),
    (r'src\tools\RegisterTool\prompt.ts', 'FIXED: register.py - RegisterTool prompt'),
    (r'src\tools\RegisterTool\spec.ts', 'FIXED: register.py - RegisterTool spec'),
    (r'src\tools\RegisterTool\types.ts', 'FIXED: register.py - RegisterTool types'),
    (r'src\tools\ScheduleCronTool\ScheduleCronTool.tsx', 'FIXED: schedule_cron_tool.py - ScheduleCronTool'),
    (r'src\tools\ScheduleCronTool\index.ts', 'FIXED: schedule_cron_tool.py - ScheduleCronTool index'),
    (r'src\tools\ScheduleCronTool\permissions.ts', 'FIXED: shell_permissions.py - ScheduleCronTool permissions'),
    (r'src\tools\ScheduleCronTool\prompt.ts', 'FIXED: schedule_cron_tool.py - ScheduleCronTool prompt'),
    (r'src\tools\ScheduleCronTool\spec.ts', 'FIXED: schedule_cron_tool.py - ScheduleCronTool spec'),
    (r'src\tools\ScheduleCronTool\types.ts', 'FIXED: schedule_cron_tool.py - ScheduleCronTool types'),
    (r'src\tools\SleepTool\SleepTool.tsx', 'FIXED: sleep_tool.py - SleepTool'),
    (r'src\tools\SleepTool\index.ts', 'FIXED: sleep_tool.py - SleepTool index'),
    (r'src\tools\SleepTool\permissions.ts', 'FIXED: shell_permissions.py - SleepTool permissions'),
    (r'src\tools\SleepTool\prompt.ts', 'FIXED: sleep_tool.py - SleepTool prompt'),
    (r'src\tools\SleepTool\spec.ts', 'FIXED: sleep_tool.py - SleepTool spec'),
    (r'src\tools\SleepTool\types.ts', 'FIXED: sleep_tool.py - SleepTool types'),
    (r'src\tools\SnipTool\SnipTool.tsx', 'FIXED: snip_tool.py - SnipTool'),
    (r'src\tools\SnipTool\index.ts', 'FIXED: snip_tool.py - SnipTool index'),
    (r'src\tools\SnipTool\permissions.ts', 'FIXED: shell_permissions.py - SnipTool permissions'),
    (r'src\tools\SnipTool\prompt.ts', 'FIXED: snip_tool.py - SnipTool prompt'),
    (r'src\tools\SnipTool\spec.ts', 'FIXED: snip_tool.py - SnipTool spec'),
    (r'src\tools\SnipTool\types.ts', 'FIXED: snip_tool.py - SnipTool types'),
    (r'src\tools\AskUserTool\AskUserTool.tsx', 'FIXED: ask_user_tool.py - AskUserTool'),
    (r'src\tools\AskUserTool\index.ts', 'FIXED: ask_user_tool.py - AskUserTool index'),
    (r'src\tools\AskUserTool\permissions.ts', 'FIXED: shell_permissions.py - AskUserTool permissions'),
    (r'src\tools\AskUserTool\prompt.ts', 'FIXED: ask_user_tool.py - AskUserTool prompt'),
    (r'src\tools\AskUserTool\spec.ts', 'FIXED: ask_user_tool.py - AskUserTool spec'),
    (r'src\tools\AskUserTool\types.ts', 'FIXED: ask_user_tool.py - AskUserTool types'),
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