"""
Type definitions for SessionMemory service.
"""

from enum import Enum
from typing import Any, Optional, Dict

from pydantic import BaseModel, Field


class MemoryScope(str, Enum):
    """Scope of the memory entry."""
    SESSION = "session"
    USER = "user"
    CROSS_SESSION = "cross_session"


class MemoryEntry(BaseModel):
    """A single memory entry."""
    key: str
    value: Any
    created_at: int
    updated_at: int
    session_id: Optional[str] = None
    expires_at: Optional[int] = None
    scope: MemoryScope = MemoryScope.SESSION


class SessionMemoryData(BaseModel):
    """Complete session memory data structure."""
    user_id: str
    entries: Dict[str, MemoryEntry] = Field(default_factory=dict)
    created_at: int
    updated_at: int
    last_summarized_message_id: Optional[str] = None
    extraction_started_at: Optional[int] = None
    tokens_at_last_extraction: int = 0
    is_initialized: bool = False


class SessionMemoryConfig(BaseModel):
    """Configuration for session memory extraction thresholds."""
    minimum_message_tokens_to_init: int = 10000
    minimum_tokens_between_update: int = 5000
    tool_calls_between_updates: int = 3


class MemoryStats(BaseModel):
    """Statistics about memory usage."""
    total_entries: int
    session_entries: int
    user_entries: int
    cross_session_entries: int
    oldest_entry_timestamp: Optional[int] = None
    newest_entry_timestamp: Optional[int] = None
    total_size_bytes: Optional[int] = None


class ManualExtractionResult(BaseModel):
    """Result of manual memory extraction."""
    success: bool
    memory_path: Optional[str] = None
    error: Optional[str] = None


__all__ = [
    "MemoryScope",
    "MemoryEntry",
    "SessionMemoryData",
    "SessionMemoryConfig",
    "MemoryStats",
    "ManualExtractionResult",
]