"""
Utility functions for SessionMemory service.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from .types import SessionMemoryData

logger = logging.getLogger(__name__)

MEMORY_DIR_NAME = ".claude"
MEMORY_FILE_NAME = "session_memory.json"
MAX_SECTION_LENGTH = 2000
MAX_TOTAL_SESSION_MEMORY_TOKENS = 12000


def get_memory_path() -> Path:
    """Get the file path for session memory storage."""
    return Path.home() / MEMORY_DIR_NAME / MEMORY_FILE_NAME


def get_memory_dir() -> Path:
    """Get the directory path for session memory storage."""
    return Path.home() / MEMORY_DIR_NAME


def ensure_memory_dir() -> None:
    """Ensure the memory directory exists with proper permissions."""
    memory_dir = get_memory_dir()
    try:
        memory_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as e:
        logger.warning(f"Failed to create memory directory: {e}")


def serialize_memory(data: SessionMemoryData) -> str:
    """Convert session memory data to JSON string."""
    return json.dumps(data.model_dump(), ensure_ascii=False, indent=2)


def deserialize_memory(json_str: str) -> Optional[SessionMemoryData]:
    """Parse JSON string into SessionMemoryData."""
    try:
        data = json.loads(json_str)
        return SessionMemoryData(**data)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to deserialize memory: {e}")
        return None


async def read_memory_file(path: Path) -> Optional[str]:
    """Read memory content from file with error handling."""
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except OSError as e:
        logger.error(f"Failed to read memory file: {e}")
    return None


async def write_memory_file(path: Path, content: str) -> bool:
    """Write memory content to file with error handling."""
    try:
        ensure_memory_dir()
        path.write_text(content, encoding="utf-8")
        return True
    except OSError as e:
        logger.error(f"Failed to write memory file: {e}")
        return False


def get_default_template() -> str:
    """Return the default session memory template."""
    return """# Session Title
_A short and distinctive 5-10 word descriptive title for the session. Super info dense, no filler_

# Current State
_What is actively being worked on right now? Pending tasks not yet completed. Immediate next steps._

# Task specification
_What did the user ask to build? Any design decisions or other explanatory context_

# Files and Functions
_What are the important files? In short, what do they contain and why are they relevant?_

# Workflow
_What bash commands are usually run and in what order? How to interpret their output if not obvious?_

# Errors & Corrections
_Errors encountered and how they were fixed. What did the user correct? What approaches failed and should not be tried again?_

# Codebase and System Documentation
_What are the important system components? How do they work/fit together?_

# Learnings
_What has worked well? What has not? What to avoid? Do not duplicate items from other sections_

# Key results
_If the user asked a specific output such as an answer to a question, a table, or other document, repeat the exact result here_

# Worklog
_Step by step, what was attempted, done? Very terse summary for each step_
"""


def truncate_content_for_section(content: str, max_chars: int) -> tuple[str, bool]:
    """Truncate content to fit within max_chars. Returns (truncated, was_truncated)."""
    if len(content) <= max_chars:
        return content, False
    
    lines = content.split('\n')
    result_lines = []
    char_count = 0
    
    for line in lines:
        if char_count + len(line) + 1 > max_chars:
            result_lines.append('\n[... section truncated for length ...]')
            return '\n'.join(result_lines), True
        result_lines.append(line)
        char_count += len(line) + 1
    
    return '\n'.join(result_lines), False


def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (4 chars per token)."""
    return len(text) // 4


def analyze_section_sizes(content: str) -> dict[str, int]:
    """Analyze section sizes in the memory content."""
    sections = {}
    lines = content.split('\n')
    current_section = ''
    current_content = []
    
    for line in lines:
        if line.startswith('# '):
            if current_section and current_content:
                section_content = '\n'.join(current_content).strip()
                sections[current_section] = estimate_token_count(section_content)
            current_section = line
            current_content = []
        else:
            current_content.append(line)
    
    if current_section and current_content:
        section_content = '\n'.join(current_content).strip()
        sections[current_section] = estimate_token_count(section_content)
    
    return sections


__all__ = [
    "get_memory_path",
    "get_memory_dir",
    "ensure_memory_dir",
    "serialize_memory",
    "deserialize_memory",
    "read_memory_file",
    "write_memory_file",
    "get_default_template",
    "truncate_content_for_section",
    "estimate_token_count",
    "analyze_section_sizes",
    "MAX_SECTION_LENGTH",
    "MAX_TOTAL_SESSION_MEMORY_TOKENS",
]