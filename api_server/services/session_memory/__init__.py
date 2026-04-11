"""
Session Memory Service - manages markdown session notes.

Provides session memory management with automatic extraction of key information
from conversations into structured markdown files.
"""

from .types import (
    MemoryScope,
    MemoryEntry,
    SessionMemoryData,
    SessionMemoryConfig,
    MemoryStats,
    ManualExtractionResult,
)

from .utils import (
    SessionMemoryUtils,
    get_memory_path,
    get_memory_dir,
    ensure_memory_dir,
    serialize_memory,
    deserialize_memory,
    get_default_template,
    estimate_token_count,
    analyze_section_sizes,
    MAX_SECTION_LENGTH,
    MAX_TOTAL_SESSION_MEMORY_TOKENS,
)

from .prompts import (
    SessionMemoryPrompts,
    get_default_update_prompt,
    generate_section_reminders,
)

from .memory import (
    SessionMemory,
    get_memory,
    set_memory,
    update_memory,
    delete_memory,
    list_sessions,
)

__all__ = [
    "MemoryScope",
    "MemoryEntry",
    "SessionMemoryData",
    "SessionMemoryConfig",
    "MemoryStats",
    "ManualExtractionResult",
    "SessionMemoryUtils",
    "SessionMemoryPrompts",
    "SessionMemory",
    "get_memory_path",
    "get_memory_dir",
    "ensure_memory_dir",
    "serialize_memory",
    "deserialize_memory",
    "get_default_template",
    "estimate_token_count",
    "analyze_section_sizes",
    "get_default_update_prompt",
    "generate_section_reminders",
    "get_memory",
    "set_memory",
    "update_memory",
    "delete_memory",
    "list_sessions",
    "MAX_SECTION_LENGTH",
    "MAX_TOTAL_SESSION_MEMORY_TOKENS",
]