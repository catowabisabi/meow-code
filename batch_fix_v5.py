import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\hooks\\useInboxPoller.ts', 'FIXED: hooks_system.py - InboxPoller, HookManager'),
    ('src\\services\\analytics\\firstPartyEventLogger.ts', 'FIXED: analytics.py - TelemetryCollector, AttributedCounter, log_event'),
    ('src\\services\\compact\\microCompact.ts', 'FIXED: compact_service.py - MicroCompact with cache_edits'),
    ('src\\utils\\sessionStorage.ts', 'FIXED: compact_service.py - SessionStorage with buffering, UUID dedup'),
    ('src\\services\\teamMemorySync\\index.ts', 'PARTIAL: No team memory sync - requires distributed system'),
    ('src\\utils\\aws.ts', 'PARTIAL: AWS integration - use boto3'),
    ('src\\utils\\agenticSessionSearch.ts', 'PARTIAL: Agentic session search - needs full-text search'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

# Get current stats
c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()
