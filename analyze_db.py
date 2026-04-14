import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

# Schema
print("=== DATABASE SCHEMA ===")
c.execute("SELECT sql FROM sqlite_master WHERE type='table'")
for row in c.fetchall():
    print(row[0])
print()

# Record counts
print("=== RECORD COUNTS ===")
c.execute("SELECT COUNT(*) FROM files")
print(f"Total records: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM files WHERE status='analyzed'")
print(f"Analyzed: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM files WHERE status='pending'")
print(f"Pending: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM files WHERE status='error'")
print(f"Error: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM files WHERE notes IS NOT NULL AND notes != ''")
print(f"With notes: {c.fetchone()[0]}")
print()

# Category distribution
print("=== CATEGORY DISTRIBUTION ===")
c.execute(r"""
    SELECT 
        CASE 
            WHEN src_path LIKE '%\tools%' THEN 'tools'
            WHEN src_path LIKE '%\commands%' THEN 'commands'
            WHEN src_path LIKE '%\cli%' THEN 'cli'
            WHEN src_path LIKE '%\utils%' THEN 'utils'
            WHEN src_path LIKE '%\hooks%' THEN 'hooks'
            WHEN src_path LIKE '%\lib%' THEN 'lib'
            WHEN src_path LIKE '%\bridge%' THEN 'bridge'
            WHEN src_path LIKE '%\services%' THEN 'services'
            WHEN src_path LIKE '%\components%' THEN 'components'
            WHEN src_path LIKE '%\tasks%' THEN 'tasks'
            ELSE 'other'
        END as category,
        COUNT(*) as count
    FROM files
    GROUP BY category
    ORDER BY count DESC
""")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}")
print()

# Severity distribution
print("=== SEVERITY DISTRIBUTION ===")
c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%CRITICAL%'")
print(f"CRITICAL: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%HIGH%'")
print(f"HIGH: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%MEDIUM%'")
print(f"MEDIUM: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%LOW%'")
print(f"LOW: {c.fetchone()[0]}")
print()

# Fixed count
print("=== FIXED STATUS ===")
c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
print(f"FIXED: {c.fetchone()[0]}")
print()

# Sample records
print("=== SAMPLE RECORDS (first 5) ===")
c.execute("SELECT src_path, category, status, SUBSTR(notes, 1, 100) FROM files LIMIT 5")
for row in c.fetchall():
    print(f"Path: {row[0]}")
    print(f"  Category: {row[1]}, Status: {row[2]}")
    print(f"  Notes: {row[3]}...")
    print()

conn.close()
