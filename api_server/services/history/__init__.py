"""
History Service - 本地會話歷史管理，支持全文搜索。
替代原本 OAuth 到 claude.ai 的設計，改為完全本地 SQLite。
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import sqlite3

from pydantic import BaseModel


class HistorySession(BaseModel):
    id: str
    user_id: str = "default"
    title: str = ""
    mode: str = "chat"
    folder: Optional[str] = None
    model: str = ""
    provider: str = ""
    message_count: int = 0
    total_tokens: int = 0
    created_at: str = ""
    updated_at: str = ""
    preview: str = ""


class HistoryMessage(BaseModel):
    id: Optional[int] = None
    session_id: str
    role: str  # user, assistant, system, tool
    content: str
    token_count: int = 0
    created_at: str = ""


class HistorySearchResult(BaseModel):
    session_id: str
    title: str
    snippet: str
    matched_at: str


class HistoryDB:
    DB_PATH = Path.home() / ".claude" / "history.db"

    def __init__(self):
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化數據庫表"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Sessions 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT DEFAULT 'default',
                title TEXT DEFAULT '',
                mode TEXT DEFAULT 'chat',
                folder TEXT,
                model TEXT DEFAULT '',
                provider TEXT DEFAULT '',
                message_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                preview TEXT DEFAULT ''
            )
        """)

        # Messages 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT CHECK(role IN ('user', 'assistant', 'system', 'tool')),
                content TEXT,
                token_count INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        # FTS5 全文搜索虛擬表
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                session_id UNINDEXED,
                content,
                tokenize='porter unicode61'
            )
        """)

        # 索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session 
            ON messages(session_id)
        """)

        conn.commit()
        conn.close()

    def create_session(self, session: HistorySession) -> HistorySession:
        """創建新會話"""
        conn = self._get_conn()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()
        session.created_at = now
        session.updated_at = now

        cursor.execute("""
            INSERT INTO sessions (id, user_id, title, mode, folder, model, provider, 
                                  message_count, total_tokens, created_at, updated_at, preview)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.id, session.user_id, session.title, session.mode, session.folder,
            session.model, session.provider, session.message_count, session.total_tokens,
            session.created_at, session.updated_at, session.preview
        ))

        conn.commit()
        conn.close()
        return session

    def get_session(self, session_id: str) -> Optional[HistorySession]:
        """獲取會話詳情"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return HistorySession(**dict(row))

    def list_sessions(
        self, 
        user_id: str = "default",
        limit: int = 50, 
        offset: int = 0,
        mode: Optional[str] = None
    ) -> List[HistorySession]:
        """列出會話（分頁）"""
        conn = self._get_conn()
        cursor = conn.cursor()

        query = "SELECT * FROM sessions WHERE user_id = ?"
        params: List = [user_id]

        if mode:
            query += " AND mode = ?"
            params.append(mode)

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [HistorySession(**dict(row)) for row in rows]

    def count_sessions(self, user_id: str = "default", mode: Optional[str] = None) -> int:
        """統計會話數量"""
        conn = self._get_conn()
        cursor = conn.cursor()

        query = "SELECT COUNT(*) FROM sessions WHERE user_id = ?"
        params: List = [user_id]

        if mode:
            query += " AND mode = ?"
            params.append(mode)

        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def update_session(self, session_id: str, **kwargs) -> bool:
        """更新會話"""
        if not kwargs:
            return False

        conn = self._get_conn()
        cursor = conn.cursor()

        kwargs['updated_at'] = datetime.utcnow().isoformat()

        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [session_id]

        cursor.execute(f"UPDATE sessions SET {set_clause} WHERE id = ?", values)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def delete_session(self, session_id: str) -> bool:
        """刪除會話及其消息"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # 刪除 FTS 記錄
        cursor.execute("DELETE FROM messages_fts WHERE session_id = ?", (session_id,))
        # 刪除消息
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        # 刪除會話
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def add_message(self, message: HistoryMessage) -> HistoryMessage:
        """添加消息"""
        conn = self._get_conn()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()
        message.created_at = now

        cursor.execute("""
            INSERT INTO messages (session_id, role, content, token_count, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            message.session_id, message.role, message.content, 
            message.token_count, message.created_at
        ))

        message.id = cursor.lastrowid

        # 更新 FTS
        cursor.execute("""
            INSERT INTO messages_fts (session_id, content)
            VALUES (?, ?)
        """, (message.session_id, message.content))

        # 更新會話統計
        cursor.execute("""
            UPDATE sessions 
            SET message_count = message_count + 1,
                total_tokens = total_tokens + ?,
                updated_at = ?
            WHERE id = ?
        """, (message.token_count, now, message.session_id))

        conn.commit()
        conn.close()
        return message

    def get_messages(
        self, 
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[HistoryMessage]:
        """獲取會話消息"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM messages 
            WHERE session_id = ?
            ORDER BY created_at ASC
            LIMIT ? OFFSET ?
        """, (session_id, limit, offset))

        rows = cursor.fetchall()
        conn.close()
        return [HistoryMessage(**dict(row)) for row in rows]

    def search(
        self, 
        query: str, 
        user_id: str = "default",
        limit: int = 20
    ) -> List[HistorySearchResult]:
        """全文搜索消息"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # 使用 FTS5 搜索
        cursor.execute("""
            SELECT m.session_id, s.title, m.content, m.created_at
            FROM messages_fts fts
            JOIN messages m ON fts.rowid = m.id
            JOIN sessions s ON m.session_id = s.id
            WHERE messages_fts MATCH ? AND s.user_id = ?
            ORDER BY rank
            LIMIT ?
        """, (query, user_id, limit))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            content = row['content']
            # 生成 snippet
            snippet = content[:200] + "..." if len(content) > 200 else content
            results.append(HistorySearchResult(
                session_id=row['session_id'],
                title=row['title'] or "Untitled",
                snippet=snippet,
                matched_at=row['created_at']
            ))

        return results

    def get_session_token_count(self, session_id: str) -> int:
        """獲取會話的總 token 數"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT total_tokens FROM sessions WHERE id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()
        return row['total_tokens'] if row else 0


# 全局實例
_history_db: Optional[HistoryDB] = None


def get_history_db() -> HistoryDB:
    global _history_db
    if _history_db is None:
        _history_db = HistoryDB()
    return _history_db
