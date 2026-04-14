import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("""
    SELECT src_path, SUBSTR(notes, 1, 150) as note_preview
    FROM files 
    WHERE notes LIKE '%CRITICAL%' 
    AND notes NOT LIKE '%FIXED:%'
    AND notes NOT LIKE '%PARTIAL:%'
    ORDER BY src_path
""")
critical = c.fetchall()

print(f"=== UNFIXED CRITICAL GAPS ({len(critical)}) ===")
for row in critical:
    print(f"\n{row[0]}")
    print(f"  {row[1]}")

conn.close()
