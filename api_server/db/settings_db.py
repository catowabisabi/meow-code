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