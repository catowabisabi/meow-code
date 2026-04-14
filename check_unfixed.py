import sqlite3
import sys
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path, notes FROM files WHERE notes NOT LIKE '%FIXED:%' LIMIT 50")
print('UNFIXED gaps (first 50):')
for i, row in enumerate(c.fetchall(), 1):
    print(f'{i}. {row[0]}')
    if row[1]:
        try:
            print(f'   {row[1][:150]}')
        except:
            print(f'   [cannot display notes]')
    print()

conn.close()