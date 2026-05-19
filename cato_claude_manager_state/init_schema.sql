PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending','dispatched','in_progress','qa_pending',
            'qa_in_progress','qa_failed','qa_passed','done','blocked','cancelled'
        )),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    related_files TEXT,
    acceptance_criteria TEXT NOT NULL,
    branch_name TEXT,
    last_commit TEXT,
    last_qa_report TEXT,
    blocked_reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status);
CREATE INDEX IF NOT EXISTS idx_todos_priority ON todos(priority);
CREATE INDEX IF NOT EXISTS idx_todos_updated ON todos(updated_at);

CREATE TRIGGER IF NOT EXISTS trg_todos_updated
AFTER UPDATE ON todos
FOR EACH ROW
BEGIN
    UPDATE todos SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TABLE IF NOT EXISTS dispatch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    todo_id INTEGER NOT NULL,
    worker TEXT NOT NULL CHECK (worker IN ('worker', 'qa')),
    dispatched_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    order_text TEXT NOT NULL,
    result_summary TEXT,
    result_status TEXT CHECK (result_status IN ('success','fail','timeout','error',NULL)),
    git_commit_before TEXT,
    git_commit_after TEXT,
    files_changed TEXT,
    FOREIGN KEY (todo_id) REFERENCES todos(id)
);

CREATE INDEX IF NOT EXISTS idx_dispatch_todo ON dispatch_history(todo_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_time ON dispatch_history(dispatched_at DESC);

CREATE TABLE IF NOT EXISTS check_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at TEXT NOT NULL DEFAULT (datetime('now')),
    current_commit TEXT,
    git_status TEXT,
    analyze_result TEXT,
    action_taken TEXT NOT NULL,
    active_todo_count INTEGER,
    summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_check_runs_time ON check_runs(checked_at DESC);

CREATE TABLE IF NOT EXISTS check_runs_daily (
    date TEXT PRIMARY KEY,
    run_count INTEGER,
    dispatch_count INTEGER,
    skip_count INTEGER,
    error_count INTEGER,
    notes TEXT
);

CREATE VIEW IF NOT EXISTS v_active_todos AS
SELECT id, title, description, priority, status,
    attempt_count, max_attempts, related_files,
    acceptance_criteria, branch_name, last_commit, last_qa_report,
    created_at, updated_at
FROM todos
WHERE status NOT IN ('done', 'cancelled')
ORDER BY
    CASE status
        WHEN 'qa_failed' THEN 1 WHEN 'qa_pending' THEN 2
        WHEN 'in_progress' THEN 3 WHEN 'dispatched' THEN 4
        WHEN 'pending' THEN 5 WHEN 'blocked' THEN 6 ELSE 9
    END, priority ASC, created_at ASC;

CREATE VIEW IF NOT EXISTS v_recent_dispatch AS
SELECT d.id, d.todo_id, t.title, d.worker, d.dispatched_at,
    d.result_status, d.git_commit_before, d.git_commit_after
FROM dispatch_history d
JOIN todos t ON t.id = d.todo_id
ORDER BY d.dispatched_at DESC LIMIT 10;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO meta (key, value) VALUES
    ('schema_version', '1'),
    ('initialized_at', datetime('now')),
    ('last_full_audit', '1970-01-01 00:00:00');