import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\test_records.db')
c = conn.cursor()

c.execute("SELECT module_name, message, error_details FROM test_results WHERE status = 'ERROR' ORDER BY module_name")
rows = c.fetchall()

print(f'Total errors: {len(rows)}')
print('\n=== Error Summary by Module ===')
for row in rows:
    print(f'\n{row[0]}:')
    print(f'  Message: {row[1][:200]}')
    if row[2]:
        lines = row[2].strip().split('\n')
        print(f'  Traceback: {lines[-1] if lines else "N/A"}')

conn.close()