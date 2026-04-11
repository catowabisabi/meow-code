"""
SessionMemory class and functions for session memory management.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict

from .types import (
    MemoryEntry,
    SessionMemoryData,
    SessionMemoryConfig,
    MemoryScope,
    MemoryStats,
)
from .utils import (
    get_memory_path,
    get_memory_dir,
    ensure_memory_dir,
    serialize_memory,
    deserialize_memory,
    read_memory_file,
    write_memory_file,
    get_default_template,
    estimate_token_count,
    MAX_SECTION_LENGTH,
    truncate_content_for_section,
    analyze_section_sizes,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = SessionMemoryConfig(
    minimum_message_tokens_to_init=10000,
    minimum_tokens_between_update=5000,
    tool_calls_between_updates=3,
)

EXTRACTION_WAIT_TIMEOUT_MS = 15000
EXTRACTION_STALE_THRESHOLD_MS = 60000


class SessionMemoryUtils:
    """Utility class for session memory operations."""
    
    @staticmethod
    def get_memory_path() -> Path:
        """Get the file path for session memory storage."""
        return get_memory_path()
    
    @staticmethod
    def get_memory_dir() -> Path:
        """Get the directory path for session memory storage."""
        return get_memory_dir()
    
    @staticmethod
    def ensure_memory_dir() -> None:
        """Ensure the memory directory exists."""
        ensure_memory_dir()
    
    @staticmethod
    def serialize_memory(data: SessionMemoryData) -> str:
        """Serialize session memory data to JSON."""
        return serialize_memory(data)
    
    @staticmethod
    def deserialize_memory(json_str: str) -> Optional[SessionMemoryData]:
        """Deserialize JSON string to session memory data."""
        return deserialize_memory(json_str)
    
    @staticmethod
    def get_default_template() -> str:
        """Get the default session memory template."""
        return get_default_template()
    
    @staticmethod
    def estimate_token_count(text: str) -> int:
        """Estimate token count for text."""
        return estimate_token_count(text)
    
    @staticmethod
    def analyze_section_sizes(content: str) -> Dict[str, int]:
        """Analyze section sizes in memory content."""
        return analyze_section_sizes(content)
    
    @staticmethod
    def truncate_for_section(content: str) -> tuple[str, bool]:
        """Truncate content for compact display."""
        max_chars = MAX_SECTION_LENGTH * 4
        return truncate_content_for_section(content, max_chars)


class SessionMemory:
    """Main class for session memory management."""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self._config = DEFAULT_CONFIG
        self._data: Optional[SessionMemoryData] = None
        self._last_summarized_message_id: Optional[str] = None
        self._extraction_started_at: Optional[int] = None
        self._tokens_at_last_extraction = 0
        self._is_initialized = False
    
    @property
    def config(self) -> SessionMemoryConfig:
        """Get current configuration."""
        return self._config
    
    def set_config(self, config: SessionMemoryConfig) -> None:
        """Set configuration."""
        self._config = config
    
    def get_data(self) -> SessionMemoryData:
        """Get or create session memory data."""
        if self._data is None:
            now = int(datetime.utcnow().timestamp() * 1000)
            self._data = SessionMemoryData(
                user_id=self.user_id,
                entries={},
                created_at=now,
                updated_at=now,
            )
        return self._data
    
    async def load(self) -> bool:
        """Load session memory from file."""
        path = get_memory_path()
        content = await read_memory_file(path)
        
        if content:
            self._data = deserialize_memory(content)
            if self._data:
                self._is_initialized = self._data.is_initialized
                self._tokens_at_last_extraction = self._data.tokens_at_last_extraction
                self._last_summarized_message_id = self._data.last_summarized_message_id
                return True
        
        return False
    
    async def save(self) -> bool:
        """Save session memory to file."""
        if self._data is None:
            return False
        
        self._data.updated_at = int(datetime.utcnow().timestamp() * 1000)
        self._data.is_initialized = self._is_initialized
        self._data.tokens_at_last_extraction = self._tokens_at_last_extraction
        self._data.last_summarized_message_id = self._last_summarized_message_id
        
        path = get_memory_path()
        content = serialize_memory(self._data)
        return await write_memory_file(path, content)
    
    async def get_memory(self, key: str, default: Any = None) -> Any:
        """Get a memory entry by key."""
        if self._data is None:
            await self.load()
        
        if self._data and key in self._data.entries:
            entry = self._data.entries[key]
            if entry.expires_at and entry.expires_at < int(datetime.utcnow().timestamp() * 1000):
                return default
            return entry.value
        
        return default
    
    async def set_memory(
        self,
        key: str,
        value: Any,
        scope: MemoryScope = MemoryScope.SESSION,
        session_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set a memory entry."""
        if self._data is None:
            await self.load()
        
        data = self.get_data()
        now = int(datetime.utcnow().timestamp() * 1000)
        
        existing_entry = data.entries.get(key)
        created_at = existing_entry.created_at if existing_entry else now
        
        expires_at = None
        if ttl_seconds:
            expires_at = now + (ttl_seconds * 1000)
        
        entry = MemoryEntry(
            key=key,
            value=value,
            created_at=created_at,
            updated_at=now,
            session_id=session_id,
            expires_at=expires_at,
            scope=scope,
        )
        
        data.entries[key] = entry
        await self.save()
    
    async def update_memory(self, key: str, value: Any, merge: bool = True) -> None:
        """Update a memory entry with optional merge."""
        if self._data is None:
            await self.load()
        
        data = self.get_data()
        now = int(datetime.utcnow().timestamp() * 1000)
        
        if key in data.entries and merge:
            existing = data.entries[key]
            if isinstance(existing.value, dict) and isinstance(value, dict):
                merged_value = {**existing.value, **value}
            else:
                merged_value = value
        else:
            merged_value = value
        
        entry = MemoryEntry(
            key=key,
            value=merged_value,
            created_at=existing.created_at if key in data.entries else now,
            updated_at=now,
            session_id=existing.session_id if key in data.entries else None,
            expires_at=existing.expires_at if key in data.entries else None,
            scope=existing.scope if key in data.entries else MemoryScope.SESSION,
        )
        
        data.entries[key] = entry
        await self.save()
    
    async def delete_memory(self, key: str) -> bool:
        """Delete a memory entry."""
        if self._data is None:
            await self.load()
        
        if self._data and key in self._data.entries:
            del self._data.entries[key]
            return await self.save()
        
        return False
    
    async def list_sessions(self) -> List[str]:
        """List all sessions with memory entries."""
        if self._data is None:
            await self.load()
        
        if not self._data:
            return []
        
        sessions = set()
        for entry in self._data.entries.values():
            if entry.session_id:
                sessions.add(entry.session_id)
        
        return list(sessions)
    
    def has_met_initialization_threshold(self, current_token_count: int) -> bool:
        """Check if initialization threshold is met."""
        return current_token_count >= self._config.minimum_message_tokens_to_init
    
    def has_met_update_threshold(self, current_token_count: int) -> bool:
        """Check if update threshold is met."""
        tokens_since = current_token_count - self._tokens_at_last_extraction
        return tokens_since >= self._config.minimum_tokens_between_update
    
    def mark_initialized(self) -> None:
        """Mark session memory as initialized."""
        self._is_initialized = True
        if self._data:
            self._data.is_initialized = True
    
    def mark_extraction_started(self) -> None:
        """Mark extraction as started."""
        self._extraction_started_at = int(datetime.utcnow().timestamp() * 1000)
        if self._data:
            self._data.extraction_started_at = self._extraction_started_at
    
    def mark_extraction_completed(self) -> None:
        """Mark extraction as completed."""
        self._extraction_started_at = None
        if self._data:
            self._data.extraction_started_at = None
    
    def record_extraction_token_count(self, token_count: int) -> None:
        """Record context size at extraction."""
        self._tokens_at_last_extraction = token_count
        if self._data:
            self._data.tokens_at_last_extraction = token_count
    
    def set_last_summarized_message_id(self, message_id: Optional[str]) -> None:
        """Set the last summarized message ID."""
        self._last_summarized_message_id = message_id
        if self._data:
            self._data.last_summarized_message_id = message_id
    
    def get_last_summarized_message_id(self) -> Optional[str]:
        """Get the last summarized message ID."""
        return self._last_summarized_message_id
    
    async def wait_for_extraction(self) -> None:
        """Wait for any in-progress extraction to complete."""
        while self._extraction_started_at:
            age = int(datetime.utcnow().timestamp() * 1000) - self._extraction_started_at
            if age > EXTRACTION_STALE_THRESHOLD_MS:
                return
            
            import asyncio
            await asyncio.sleep(1)
    
    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        if self._data is None:
            return MemoryStats(
                total_entries=0,
                session_entries=0,
                user_entries=0,
                cross_session_entries=0,
            )
        
        entries = list(self._data.entries.values())
        session_count = sum(1 for e in entries if e.scope == MemoryScope.SESSION)
        user_count = sum(1 for e in entries if e.scope == MemoryScope.USER)
        cross_count = sum(1 for e in entries if e.scope == MemoryScope.CROSS_SESSION)
        
        timestamps = [e.updated_at for e in entries]
        oldest = min(timestamps) if timestamps else None
        newest = max(timestamps) if timestamps else None
        
        return MemoryStats(
            total_entries=len(entries),
            session_entries=session_count,
            user_entries=user_count,
            cross_session_entries=cross_count,
            oldest_entry_timestamp=oldest,
            newest_entry_timestamp=newest,
        )
    
    async def reset(self) -> None:
        """Reset session memory state."""
        self._config = DEFAULT_CONFIG
        self._data = None
        self._last_summarized_message_id = None
        self._extraction_started_at = None
        self._tokens_at_last_extraction = 0
        self._is_initialized = False


_memory_instance: Optional[SessionMemory] = None


def get_memory(user_id: str = "default") -> SessionMemory:
    """Get the singleton session memory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = SessionMemory(user_id)
    return _memory_instance


def set_memory(
    key: str,
    value: Any,
    user_id: str = "default",
    **kwargs,
) -> None:
    """Set a memory entry."""
    memory = get_memory(user_id)
    return memory.set_memory(key, value, **kwargs)


def update_memory(key: str, value: Any, user_id: str = "default", **kwargs) -> None:
    """Update a memory entry."""
    memory = get_memory(user_id)
    return memory.update_memory(key, value, **kwargs)


def delete_memory(key: str, user_id: str = "default") -> bool:
    """Delete a memory entry."""
    memory = get_memory(user_id)
    return memory.delete_memory(key)


def list_sessions(user_id: str = "default") -> List[str]:
    """List all sessions with memory entries."""
    memory = get_memory(user_id)
    return memory.list_sessions()


__all__ = [
    "SessionMemory",
    "SessionMemoryUtils",
    "get_memory",
    "set_memory",
    "update_memory",
    "delete_memory",
    "list_sessions",
]