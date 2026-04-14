import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

# Get all unfixed gaps
print("=== UNFIXED CRITICAL GAPS ===")
c.execute("""
    SELECT src_path, notes 
    FROM files 
    WHERE notes LIKE '%CRITICAL%' 
    AND notes NOT LIKE '%FIXED:%'
    ORDER BY src_path
""")
critical = c.fetchall()
print(f"Total CRITICAL: {len(critical)}")
for row in critical:
    print(f"\n{row[0]}")
    if row[1]:
        print(f"  {row[1][:200]}")

print("\n\n=== UNFIXED HIGH GAPS (first 50) ===")
c.execute("""
    SELECT src_path, notes 
    FROM files 
    WHERE notes LIKE '%HIGH%' 
    AND notes NOT LIKE '%FIXED:%'
    ORDER BY src_path
    LIMIT 50
""")
high = c.fetchall()
print(f"Showing first 50 of {len(high)+50} total HIGH gaps")
for row in high[:20]:
    print(f"\n{row[0]}")
    if row[1]:
        print(f"  {row[1][:150]}")

conn.close()
