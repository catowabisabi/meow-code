import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\cli\\exit.ts', 'FIXED: cli_utils.py - GracefulShutdown handler'),
    ('src\\cli\\print.ts', 'FIXED: cli_utils.py - FeatureFlags infrastructure'),
    ('src\\commands\\init.ts', 'FIXED: commands.py - InitCommand with interactive wizard'),
    ('src\\commands\\branch\\branch.ts', 'FIXED: commands.py - BranchCommand with worktree management'),
    ('src\\components\\GlobalSearchDialog.tsx', 'PARTIAL: React UI component - requires frontend'),
    ('src\\components\\IdeOnboardingDialog.tsx', 'PARTIAL: React UI component - requires frontend'),
    ('src\\components\\QuickOpenDialog.tsx', 'PARTIAL: React UI component - requires frontend'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()
