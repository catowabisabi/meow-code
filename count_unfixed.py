import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

# Total gaps
c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%CRITICAL%' OR notes LIKE '%HIGH%' OR notes LIKE '%MEDIUM%'")
total_gaps = c.fetchone()[0]

# Fixed gaps
c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED:%'")
fixed = c.fetchone()[0]

# Unfixed gaps
unfixed = total_gaps - fixed

print(f'Total gaps (CRITICAL/HIGH/MEDIUM): {total_gaps}')
print(f'Fixed: {fixed}')
print(f'Unfixed: {unfixed}')

# Breakdown by severity
c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%CRITICAL%' AND notes NOT LIKE '%FIXED:%'")
critical_unfixed = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%HIGH%' AND notes NOT LIKE '%FIXED:%'")
high_unfixed = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%MEDIUM%' AND notes NOT LIKE '%FIXED:%'")
medium_unfixed = c.fetchone()[0]

print(f'\nUnfixed by severity:')
print(f'  CRITICAL: {critical_unfixed}')
print(f'  HIGH: {high_unfixed}')
print(f'  MEDIUM: {medium_unfixed}')

conn.close()
