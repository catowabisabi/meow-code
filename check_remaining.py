import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

c.execute("SELECT src_path, SUBSTR(notes, 1, 200) FROM files WHERE notes NOT LIKE '%FIXED%' AND notes IS NOT NULL AND notes != '' ORDER BY RANDOM() LIMIT 60")
print('Sample unfixed gaps with notes:')
for i, row in enumerate(c.fetchall(), 1):
    print(f'{i}. {row[0]}')
    if row[1]:
        print(f'   {row[1]}')
    print()

conn.close()