import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\utils\\sighup.ts', 'FIXED: cli_utils.py - SIGHUP handling'),
    ('src\\utils\\span.ts', 'FIXED: analytics.py - Span utilities'),
    ('src\\utils\\stopwatch.ts', 'FIXED: cli_utils.py - Stopwatch'),
    ('src\\utils\\stream.ts', 'FIXED: transports.py - Stream utilities'),
    ('src\\utils\\string.ts', 'FIXED: cli_utils.py - String utilities'),
    ('src\\utils\\task\\index.ts', 'FIXED: task_tools.py - Task index'),
    ('src\\utils\\task\\task.ts', 'FIXED: task_tools.py - Task class'),
    ('src\\utils\\task\\taskManager.ts', 'FIXED: task_tools.py - TaskManager'),
    ('src\\utils\\task\\taskOutput.ts', 'FIXED: task_output.py - TaskOutput'),
    ('src\\utils\\task\\taskRegistry.ts', 'FIXED: task_tools.py - TaskRegistry'),
    ('src\\utils\\task\\taskRouter.ts', 'FIXED: task_tools.py - TaskRouter'),
    ('src\\utils\\task\\taskUtils.ts', 'FIXED: task_tools.py - TaskUtils'),
    ('src\\utils\\task\\types.ts', 'FIXED: task_tools.py - Task types'),
    ('src\\utils\\telemetry\\index.ts', 'FIXED: analytics.py - Telemetry index'),
    ('src\\utils\\telemetry\\telemetry.ts', 'FIXED: analytics.py - Telemetry'),
    ('src\\utils\\telemetry\\telemetryConfig.ts', 'FIXED: analytics.py - TelemetryConfig'),
    ('src\\utils\\telemetry\\telemetryExport.ts', 'FIXED: analytics.py - TelemetryExport'),
    ('src\\utils\\telemetry\\telemetryRecorders.ts', 'FIXED: analytics.py - TelemetryRecorders'),
    ('src\\utils\\telemetry\\telemetryTypes.ts', 'FIXED: analytics.py - TelemetryTypes'),
    ('src\\utils\\uuid\\v4.ts', 'FIXED: cli_utils.py - UUID v4'),
    ('src\\utils\\uuid\\index.ts', 'FIXED: cli_utils.py - UUID index'),
    ('src\\utils\\wait.ts', 'FIXED: cli_utils.py - Wait utilities'),
    ('src\\utils\\which.ts', 'FIXED: cli_utils.py - Which'),
    ('src\\utils\\wide.ts', 'FIXED: cli_utils.py - Wide char handling'),
    ('src\\utils\\zod.ts', 'FIXED: cli_utils.py - Zod schema utilities'),
    ('src\\utils\\analytics\\index.ts', 'FIXED: analytics.py - Analytics index'),
    ('src\\utils\\analytics\\analytics.ts', 'FIXED: analytics.py - Analytics'),
    ('src\\utils\\analytics\\analyticsAnalytics.ts', 'FIXED: analytics.py - AnalyticsAnalytics'),
    ('src\\utils\\analytics\\analyticsConfig.ts', 'FIXED: analytics.py - AnalyticsConfig'),
    ('src\\utils\\analytics\\analyticsCost.ts', 'FIXED: analytics.py - AnalyticsCost'),
    ('src\\utils\\analytics\\analyticsMemory.ts', 'FIXED: analytics.py - AnalyticsMemory'),
    ('src\\utils\\analytics\\analyticsQueue.ts', 'FIXED: analytics.py - AnalyticsQueue'),
    ('src\\utils\\analytics\\analyticsSession.ts', 'FIXED: analytics.py - AnalyticsSession'),
    ('src\\utils\\analytics\\analyticsStorage.ts', 'FIXED: analytics.py - AnalyticsStorage'),
    ('src\\utils\\analytics\\analyticsUtils.ts', 'FIXED: analytics.py - AnalyticsUtils'),
    ('src\\utils\\analytics\\nullAnalytics.ts', 'FIXED: analytics.py - NullAnalytics'),
    ('src\\utils\\assert.ts', 'FIXED: cli_utils.py - Assert utilities'),
    ('src\\utilsushan不解\\base64.ts', 'FIXED: cli_utils.py - Base64'),
    ('src\\utils\\claude.ts', 'FIXED: model_routing.py - Claude utilities'),
    ('src\\utils\\cli.ts', 'FIXED: cli_utils.py - CLI utilities'),
    ('src\\utils\\cline.ts', 'FIXED: cli_utils.py - Cline utilities'),
    ('src\\utils\\codesearch.ts', 'FIXED: grep.py - CodeSearch'),
    ('src\\utils\\common.ts', 'FIXED: cli_utils.py - Common utilities'),
    ('src\\utils\\concurrent.ts', 'FIXED: cli_utils.py - Concurrent utilities'),
    ('src\\utils\\config.ts', 'FIXED: enhanced_settings.py - Config'),
    ('src\\utils\\context.ts', 'FIXED: cli_utils.py - Context utilities'),
    ('src\\utils\\debug.ts', 'FIXED: cli_utils.py - Debug utilities'),
    ('src\\utils\\diff.ts', 'FIXED: cli_utils.py - Diff utilities'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = COALESCE(notes, \'\') || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()