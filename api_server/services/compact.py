"""Context Compression Service.
Compresses conversation history when it gets too long.
Strategy: Keep system prompt + last N messages, summarize the rest.
"""
import re
from dataclasses import dataclass
from typing import List, Union

from ..models.message import Message
from ..models.content_block import ContentBlock, TextBlock


@dataclass
class CompactResult:
    compacted_messages: List[Message]
    summary: str
    original_count: int
    compacted_count: int


def _extract_text(content: Union[str, List[ContentBlock]]) -> str:
    """Extract plain text from a message's content blocks."""
    if isinstance(content, str):
        return content
    return " ".join(
        block.text for block in content
        if isinstance(block, TextBlock) or (isinstance(block, dict) and block.get("type") == "text")
    )


def should_compact(messages: List[Message], threshold: int = 40) -> bool:
    """Check whether compaction is needed based on message count."""
    return len(messages) > threshold


def build_summary(messages: List[Message]) -> str:
    """Build a human-readable summary from a list of messages.
    Extracts key decisions, file paths mentioned, and task progress.
    """
    parts: List[str] = []
    file_paths: set = set()
    decisions: List[str] = []

    for msg in messages:
        text = _extract_text(msg.content)
        if not text:
            continue

        # Extract file paths (Unix and Windows style)
        path_matches = re.findall(r'(?:/[\w.-]+(?:/[\w.-]+)+|[A-Z]:\\[\w.-]+(?:\\[\w.-]+)+)', text)
        for p in path_matches:
            file_paths.add(p)

        # Keep short summaries of user messages as task context
        if msg.role == "user":
            trimmed = text[:150].strip()
            if trimmed:
                parts.append(f"User: {trimmed}")

        # Keep short summaries of assistant conclusions
        if msg.role == "assistant":
            trimmed = text[:200].strip()
            if trimmed:
                decisions.append(trimmed)

    sections: List[str] = []

    if parts:
        sections.append("Tasks discussed:\n" + "\n".join(f"- {p}" for p in parts))

    if decisions:
        # Keep only last few decisions to stay concise
        recent = decisions[-5:]
        sections.append("Key points:\n" + "\n".join(f"- {d}" for d in recent))

    if file_paths:
        paths = list(file_paths)[:20]
        sections.append("Files referenced:\n" + "\n".join(f"- {p}" for p in paths))

    result = "\n\n".join(sections)
    return result if result else "Previous conversation with no extractable context."


def compact_messages(
    messages: List[Message],
    max_messages: int = 40,
    keep_recent: int = 10,
) -> CompactResult:
    """Compress conversation history when it gets too long.
    Keeps the last `keep_recent` messages and summarizes the rest
    into a single user message.
    """
    original_count = len(messages)

    # No compaction needed
    if len(messages) <= max_messages:
        return CompactResult(
            compacted_messages=messages,
            summary="",
            original_count=original_count,
            compacted_count=len(messages),
        )

    # Separate system messages (always keep them)
    system_messages = [m for m in messages if m.role == "system"]
    non_system_messages = [m for m in messages if m.role != "system"]

    # Split into older messages (to summarize) and recent messages (to keep)
    cutoff = len(non_system_messages) - keep_recent
    older_messages = non_system_messages[:cutoff]
    recent_messages = non_system_messages[cutoff:]

    # Build summary from older messages
    summary = build_summary(older_messages)

    # Create summary message
    summary_message = Message(
        role="user",
        content=f"[Previous conversation summary: {summary}]",
    )

    # Reassemble: system messages + summary + recent
    compacted_messages: List[Message] = [
        *system_messages,
        summary_message,
        *recent_messages,
    ]

    return CompactResult(
        compacted_messages=compacted_messages,
        summary=summary,
        original_count=original_count,
        compacted_count=len(compacted_messages),
    )
