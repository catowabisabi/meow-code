import sqlite3

conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
cur = conn.cursor()

# Get pending files grouped by category
cur.execute('''
    SELECT 
        CASE 
            WHEN src_path LIKE 'src/cli/%' THEN 'cli'
            WHEN src_path LIKE 'src/commands/%' THEN 'commands'
            WHEN src_path LIKE 'src/utils/%' THEN 'utils'
            WHEN src_path LIKE 'src/types/%' THEN 'types'
            WHEN src_path LIKE 'src/models/%' THEN 'models'
            WHEN src_path LIKE 'src/sessions/%' THEN 'sessions'
            WHEN src_path LIKE 'src/bridge/%' THEN 'bridge'
            WHEN src_path LIKE 'src/main%' THEN 'main'
            ELSE 'other'
        END as category,
        COUNT(*) as count
    FROM files 
    WHERE status="pending"
    GROUP BY category
    ORDER BY count DESC
''')

print("Pending files by category:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Get specific files to analyze next round
cur.execute('SELECT src_path FROM files WHERE status="pending" ORDER BY src_path LIMIT 50')
pending_files = [r[0] for r in cur.fetchall()]

print(f"\nFirst 50 pending files to analyze:")
for f in pending_files[:50]:
    print(f"  {f}")