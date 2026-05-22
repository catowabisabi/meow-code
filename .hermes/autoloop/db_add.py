import sqlite3
conn = sqlite3.connect('.hermes/autoloop/progress.db')
cur = conn.cursor()

# Update HistoryPage todo to pending (it's a larger feature - session message view needed first)
cur.execute("""UPDATE todo SET status='pending' WHERE id=13""")

# Add a new more specific todo for the annotation button in MessageBubble
cur.execute("""INSERT INTO todo (title, detail, priority, status, source) VALUES (?, ?, ?, ?, ?)""",
    ('MessageBubble — add "Add note" annotation button for user messages',
     'MessageBubble.tsx displays paste_ref annotations (line 573-585) but has no UI to create them. Need: a small annotation button (+) that opens an inline input to add a note/paste_ref annotation to any user message. historyApi.createAnnotation(messageId, type, content) already exists.',
     3, 'new', 'feature-gap'))

conn.commit()
print('Updated todo 13 -> pending')
print('Added new todo for annotation button')

cur.execute('SELECT id, title, status, priority FROM todo WHERE status IN ("pending","new") ORDER BY priority DESC, rowid ASC')
print('Pending/New todos:')
for r in cur.fetchall(): print(r)