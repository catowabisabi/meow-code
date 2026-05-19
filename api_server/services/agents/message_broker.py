import sqlite3
import json
import time
import uuid
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio

class MessagePriority(Enum):
    HIGH = 1
    NORMAL = 2
    LOW = 3

@dataclass
class Message:
    id: str
    source_agent: str
    target_agent: str
    message_type: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    created_at: float = field(default_factory=time.time)
    delivered: bool = False
    delivery_attempts: int = 0
    last_attempt_at: Optional[float] = None

class MessageBroker:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = ".cato/message_broker.db"
        
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self._pending_queue: asyncio.Queue = asyncio.Queue()
        self._in_memory_messages: Dict[str, Message] = {}
        
        self._ensure_db()

    def _ensure_db(self):
        import os
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                source_agent TEXT NOT NULL,
                target_agent TEXT NOT NULL,
                message_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                priority INTEGER NOT NULL,
                created_at REAL NOT NULL,
                delivered INTEGER NOT NULL DEFAULT 0,
                delivery_attempts INTEGER NOT NULL DEFAULT 0,
                last_attempt_at REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_target_agent 
            ON messages(target_agent)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_priority 
            ON messages(priority)
        """)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
        return self._conn

    async def publish(
        self,
        source_agent: str,
        target_agent: str,
        message_type: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> str:
        message_id = str(uuid.uuid4())
        
        message = Message(
            id=message_id,
            source_agent=source_agent,
            target_agent=target_agent,
            message_type=message_type,
            payload=payload,
            priority=priority,
        )
        
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO messages 
            (id, source_agent, target_agent, message_type, payload, priority, created_at, delivered, delivery_attempts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.id,
            message.source_agent,
            message.target_agent,
            message.message_type,
            json.dumps(message.payload),
            message.priority.value,
            message.created_at,
            0,
            0,
        ))
        conn.commit()
        
        self._in_memory_messages[message_id] = message
        await self._pending_queue.put(message)
        
        await self._notify_subscribers(target_agent, message)
        
        return message_id

    async def subscribe(
        self,
        agent_id: str,
        callback: Callable[[Message], Any],
    ):
        self._subscriptions[agent_id].append(callback)

    async def _notify_subscribers(self, agent_id: str, message: Message):
        if agent_id in self._subscriptions:
            for callback in self._subscriptions[agent_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception:
                    pass

    async def get_messages(
        self,
        agent_id: str,
        limit: int = 100,
        only_unread: bool = False,
    ) -> List[Message]:
        conn = self._get_conn()
        
        query = """
            SELECT id, source_agent, target_agent, message_type, payload, 
                   priority, created_at, delivered, delivery_attempts, last_attempt_at
            FROM messages
            WHERE target_agent = ?
        """
        params = [agent_id]
        
        if only_unread:
            query += " AND delivered = 0"
        
        query += " ORDER BY priority ASC, created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        messages = []
        for row in rows:
            message = Message(
                id=row[0],
                source_agent=row[1],
                target_agent=row[2],
                message_type=row[3],
                payload=json.loads(row[4]),
                priority=MessagePriority(row[5]),
                created_at=row[6],
                delivered=bool(row[7]),
                delivery_attempts=row[8],
                last_attempt_at=row[9],
            )
            messages.append(message)
        
        return messages

    async def mark_delivered(self, message_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("""
            UPDATE messages 
            SET delivered = 1, last_attempt_at = ?
            WHERE id = ?
        """, (time.time(), message_id))
        conn.commit()
        
        if message_id in self._in_memory_messages:
            self._in_memory_messages[message_id].delivered = True
        
        return cursor.rowcount > 0

    async def get_pending_count(self, agent_id: str) -> int:
        conn = self._get_conn()
        cursor = conn.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE target_agent = ? AND delivered = 0
        """, (agent_id,))
        row = cursor.fetchone()
        return row[0] if row else 0

    async def requeue_pending(self, agent_id: str) -> int:
        conn = self._get_conn()
        cursor = conn.execute("""
            UPDATE messages 
            SET delivery_attempts = delivery_attempts + 1,
                last_attempt_at = ?
            WHERE target_agent = ? AND delivered = 0
        """, (time.time(), agent_id))
        conn.commit()
        
        return cursor.rowcount

_broker: Optional[MessageBroker] = None

def get_message_broker() -> MessageBroker:
    global _broker
    if _broker is None:
        _broker = MessageBroker()
    return _broker