import sqlite3
from pathlib import Path
from typing import Optional
import json

DB_PATH = Path(__file__).parent.parent / "user_settings.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # API credentials table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT UNIQUE NOT NULL,
            api_key TEXT,
            base_url TEXT,
            extra_config TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def get_setting(key: str) -> Optional[str]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else None

def set_setting(key: str, value: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()
    conn.close()

def get_api_credential(provider: str) -> Optional[dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM api_credentials WHERE provider = ?", (provider,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def set_api_credential(provider: str, api_key: str, base_url: str = None, extra_config: dict = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO api_credentials (provider, api_key, base_url, extra_config)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(provider) DO UPDATE SET
            api_key = excluded.api_key,
            base_url = excluded.base_url,
            extra_config = excluded.extra_config
    """, (provider, api_key, base_url, json.dumps(extra_config) if extra_config else None))
    conn.commit()
    conn.close()

def has_any_api_key() -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM api_credentials WHERE api_key IS NOT NULL AND api_key != ''")
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_all_api_credentials() -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM api_credentials WHERE api_key IS NOT NULL AND api_key != ''")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ─── Issues Database ───────────────────────────────────────────────────────────

ISSUES_DB_PATH = Path(__file__).parent.parent / "issues.db"

def get_issues_db():
    conn = sqlite3.connect(ISSUES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_issues_db():
    conn = get_issues_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            severity TEXT NOT NULL CHECK(severity IN ('critical', 'high', 'medium', 'low')),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            file_path TEXT,
            line_number INTEGER,
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'fixed', 'wontfix')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            test_plan TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_name TEXT UNIQUE NOT NULL,
            endpoint TEXT NOT NULL,
            expected_status INTEGER,
            description TEXT,
            last_run TIMESTAMP,
            last_status TEXT,
            last_error TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def add_issue(
    issue_id: str,
    category: str,
    severity: str,
    title: str,
    description: str,
    file_path: str = None,
    line_number: int = None,
    test_plan: str = None,
) -> None:
    conn = get_issues_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO issues (issue_id, category, severity, title, description, file_path, line_number, test_plan)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (issue_id, category, severity, title, description, file_path, line_number, test_plan))
    conn.commit()
    conn.close()

def get_all_issues() -> list:
    conn = get_issues_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_issues_by_status(status: str) -> list:
    conn = get_issues_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues WHERE status = ? ORDER BY created_at DESC", (status,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_issue_status(issue_id: str, status: str) -> None:
    conn = get_issues_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE issues SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE issue_id = ?
    """, (status, issue_id))
    conn.commit()
    conn.close()

def record_health_check(check_name: str, status: str, error: str = None) -> None:
    conn = get_issues_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO health_checks (check_name, last_run, last_status, last_error)
        VALUES (?, CURRENT_TIMESTAMP, ?, ?)
        ON CONFLICT(check_name) DO UPDATE SET
            last_run = CURRENT_TIMESTAMP,
            last_status = excluded.last_status,
            last_error = excluded.last_error
    """, (check_name, status, error))
    conn.commit()
    conn.close()