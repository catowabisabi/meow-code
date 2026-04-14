import sqlite3, datetime

db = sqlite3.connect(r"F:\codebase\cato-claude\progress.db")

db.execute("ALTER TABLE files ADD COLUMN source TEXT DEFAULT 'typescript'")
db.execute("ALTER TABLE files ADD COLUMN category TEXT")
db.execute("ALTER TABLE files ADD COLUMN python_api_path TEXT")

db.execute("""
CREATE TABLE IF NOT EXISTS python_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    python_path TEXT NOT NULL,
    typescript_source TEXT,
    status TEXT DEFAULT 'pending',
    summary TEXT,
    category TEXT,
    gaps TEXT,
    analyzed_at TEXT,
    notes TEXT
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS gap_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    typescript_feature TEXT NOT NULL,
    python_equivalent TEXT,
    gap_description TEXT,
    priority TEXT,
    created_at TEXT
)
""")

db.execute("UPDATE files SET source = 'typescript' WHERE source IS NULL")

db.commit()
print("Schema updated successfully")

print("\nTables:")
print(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())

print("\nFiles count by source:")
print(db.execute("SELECT source, COUNT(*) FROM files GROUP BY source").fetchall())

db.close()