import sqlite3
conn = sqlite3.connect('.hermes/autoloop/progress.db')
cur = conn.cursor()

# Add painpoint
cur.execute("""INSERT INTO painpoint (content, severity) VALUES (?, ?)""",
    ('HistoryPage.tsx has updateMessage + createAnnotation API calls in historyApi.ts but HistoryPage.tsx itself never calls them. No edit button on messages, no annotation UI. Users cannot edit history messages or add paste references.', 3))
conn.commit()
print('Painpoint added:', cur.lastrowid)

# Add todo
cur.execute("""INSERT INTO todo (title, detail, priority, status, source) VALUES (?, ?, ?, ?, ?)""",
    ('HistoryPage message editing — add inline edit + annotation UI',
     'HistoryPage.tsx has unused historyApi.updateMessage + createAnnotation. Add: (1) edit button on each message bubble, (2) inline edit mode with save/cancel, (3) annotation button to add paste references or notes to any message. The APIs already exist server-side.',
     2, 'new', 'painpoint-rectification'))
conn.commit()
print('Todo added:', cur.lastrowid)

# Mark the adaptive error recovery todo as pending (it needs more planning before dispatch)
cur.execute("""UPDATE todo SET status='pending' WHERE id=12""")
conn.commit()
print('Updated todo 12 -> pending')

# Show all pending/new
cur.execute('SELECT id, title, status FROM todo WHERE status IN ("pending","new") ORDER BY priority DESC, rowid ASC')
print('Pending/New todos:')
for r in cur.fetchall(): print(r)