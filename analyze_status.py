import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM files WHERE notes IS NULL OR notes = ''")
print('No notes:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
print('FIXED:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%PARTIAL%'")
print('PARTIAL:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%NO_MATCH%'")
print('NO_MATCH:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM files WHERE notes NOT LIKE '%FIXED%' AND notes NOT LIKE '%PARTIAL%' AND notes NOT LIKE '%NO_MATCH%' AND notes IS NOT NULL AND notes != ''")
print('Has notes but not FIXED/PARTIAL/NO_MATCH:', c.fetchone()[0])

conn.close()