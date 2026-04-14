import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    ('src\\utils\\shell\\bashProvider.ts', 'FIXED: bash_provider.py - BashRCLoader, BashProvider with RC file sourcing'),
    ('src\\utils\\sandbox\\sandbox-adapter.ts', 'FIXED: sandbox_adapter.py - SandboxManager, bare_git_repo_scrub_paths'),
    ('src\\tools\\GlobTool\\GlobTool.ts', 'FIXED: glob_tool.py - GlobTool with async glob'),
    ('src\\tools\\BashTool\\shouldUseSandbox.ts', 'FIXED: sandbox_adapter.py - should_use_sandbox'),
    ('src\\tools\\WebFetchTool\\preapproved.ts', 'FIXED: webfetch_tool.py - PREAPPROVED_DOMAINS (50+ domains)'),
    ('src\\tools\\WebFetchTool\\utils.ts', 'FIXED: webfetch_tool.py - validate_url, is_url_preapproved'),
]

for path, fix in fixes:
    c.execute('UPDATE files SET notes = notes || ? WHERE src_path = ?', (f' | {fix}', path))

conn.commit()
print(f'Updated {len(fixes)} records')

conn.close()
