"""
Memory extraction service - main module.
Extracts durable memories from conversations and writes them to the auto-memory directory.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from pydantic import BaseModel

from .memory_extractor import MemoryExtractor
from .memory_analyzer import MemoryAnalyzer
from .memory_classifier import MemoryClassifier
from .prompts import ExtractionPrompts


class ExtractedMemory(BaseModel):
    id: str
    memory_type: str
    content: str
    source_session: Optional[str] = None
    source_message_idx: Optional[int] = None
    createdAt: int
    tags: List[str] = []
    importance: float = 0.5
    priority: str = "medium"
    categories: List[str] = []


class ExtractionResult(BaseModel):
    id: str
    memory_type: str
    content: str
    importance: float
    source_session: Optional[str] = None
    source_message_idx: Optional[int] = None
    createdAt: int
    tags: List[str] = []
    priority: str = "medium"
    categories: List[str] = []
    analysis_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.memory_type,
            "content": self.content,
            "importance": self.importance,
            "source_session": self.source_session,
            "source_message_idx": self.source_message_idx,
            "createdAt": self.createdAt,
            "tags": self.tags,
            "priority": self.priority,
            "categories": self.categories,
            "analysis_metadata": self.analysis_metadata,
        }


class MemoryExtractionConfig(BaseModel):
    min_importance: float = 0.7
    max_memories_per_session: int = 20
    extract_types: List[str] = ["fact", "decision", "preference", "context"]
    enable_analysis: bool = True
    enable_ranking: bool = True
    project_context: Optional[str] = None


def _get_memories_dir() -> Path:
    return Path.home() / ".claude" / "extracted_memories"


async def _ensure_memories_dir() -> None:
    d = _get_memories_dir()
    d.mkdir(parents=True, exist_ok=True)


class ExtractMemoriesService:
    """
    Service for extracting memories from conversations.
    """

    _extractor = MemoryExtractor()
    _analyzer = MemoryAnalyzer()
    _classifier = MemoryClassifier()

    @staticmethod
    async def extract_from_text(
        text: str,
        session_id: Optional[str] = None,
        message_idx: Optional[int] = None,
        config: Optional[MemoryExtractionConfig] = None,
    ) -> List[ExtractedMemory]:
        """
        Extract memories from a single text input.

        Args:
            text: Text content to extract from
            session_id: Optional session identifier
            message_idx: Optional message index
            config: Optional extraction configuration

        Returns:
            List of ExtractedMemory objects
        """
        if not text or len(text.strip()) < 10:
            return []

        config = config or MemoryExtractionConfig()

        internal_memories = ExtractMemoriesService._extractor.extract_memories_from_message(
            content=text,
            session_id=session_id,
            message_idx=message_idx,
        )

        memories = []
        for mem in internal_memories:
            if mem.importance >= config.min_importance:
                memories.append(ExtractedMemory(
                    id=mem.id,
                    memory_type=mem.memory_type,
                    content=mem.content,
                    importance=mem.importance,
                    source_session=mem.source_session,
                    source_message_idx=mem.source_message_idx,
                    createdAt=mem.createdAt,
                    tags=mem.tags,
                    priority=mem.priority,
                    categories=mem.categories,
                ))

        return memories[:config.max_memories_per_session]

    @staticmethod
    async def extract_from_conversation(
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        config: Optional[MemoryExtractionConfig] = None,
    ) -> ExtractionResult:
        """
        Extract memories from a conversation.

        Args:
            messages: List of message dictionaries with 'content' and optional metadata
            session_id: Optional session identifier
            config: Optional extraction configuration

        Returns:
            ExtractionResult with extracted memories and analysis
        """
        config = config or MemoryExtractionConfig()

        internal_result = ExtractMemoriesService._extractor.extract_memories_from_conversation(
            messages=messages,
            session_id=session_id,
            config={
                "min_importance": config.min_importance,
                "max_memories": config.max_memories_per_session,
                "project_context": config.project_context,
            },
        )

        memories = []
        for mem in internal_result.memories:
            memories.append(ExtractedMemory(
                id=mem.id,
                memory_type=mem.memory_type,
                content=mem.content,
                importance=mem.importance,
                source_session=mem.source_session,
                source_message_idx=mem.source_message_idx,
                createdAt=mem.createdAt,
                tags=mem.tags,
                priority=mem.priority,
                categories=mem.categories,
            ))

        analysis_metadata = None
        if config.enable_analysis and internal_result.analysis:
            summary = ExtractMemoriesService._analyzer.get_memory_summary(
                [m.to_dict() for m in internal_result.memories]
            )
            analysis_metadata = {
                "extraction_time_ms": internal_result.extraction_time_ms,
                "messages_processed": internal_result.messages_processed,
                "total_memories": summary.total_memories,
                "by_category": summary.by_category,
                "by_priority": summary.by_priority,
            }

        return ExtractionResult(
            id=f"extraction_{datetime.utcnow().timestamp()}",
            memory_type="extraction_session",
            content=f"Extracted {len(memories)} memories from conversation",
            importance=0.5,
            createdAt=int(datetime.utcnow().timestamp() * 1000),
            tags=["extraction", "batch"],
            analysis_metadata=analysis_metadata,
        )

    @staticmethod
    async def save_memory(memory: ExtractedMemory) -> None:
        """
        Save a single memory.

        Args:
            memory: ExtractedMemory to save
        """
        await _ensure_memories_dir()

        try:
            from ..services.memory import MemoryService, MemoryInput
            await MemoryService.save_memory(MemoryInput(
                type=f"extracted_{memory.memory_type}",
                name=f"extracted_{memory.id}",
                description=memory.content[:100],
                content=memory.content,
            ))
        except Exception:
            pass

    @staticmethod
    async def save_memories(memories: List[ExtractedMemory]) -> None:
        """
        Save multiple memories.

        Args:
            memories: List of ExtractedMemory objects to save
        """
        for memory in memories:
            await ExtractMemoriesService.save_memory(memory)

    @staticmethod
    async def get_extraction_stats(
        memories: List[ExtractedMemory],
    ) -> Dict[str, Any]:
        """
        Get statistics about extracted memories.

        Args:
            memories: List of memories to analyze

        Returns:
            Dictionary with statistics
        """
        if not memories:
            return {
                "total": 0,
                "by_type": {},
                "by_priority": {},
                "average_importance": 0.0,
            }

        by_type: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}
        total_importance = 0.0

        for mem in memories:
            by_type[mem.memory_type] = by_type.get(mem.memory_type, 0) + 1
            by_priority[mem.priority] = by_priority.get(mem.priority, 0) + 1
            total_importance += mem.importance

        return {
            "total": len(memories),
            "by_type": by_type,
            "by_priority": by_priority,
            "average_importance": total_importance / len(memories),
        }

    @staticmethod
    def get_prompts() -> ExtractionPrompts:
        """
        Get the extraction prompts provider.

        Returns:
            ExtractionPrompts instance
        """
        return ExtractionPrompts

    @staticmethod
    def create_auto_mem_can_use_tool(
        memory_dir: str,
    ) -> Callable[[Any, Dict[str, Any]], Dict[str, Any]]:
        """
        Create a canUseTool function for auto-memory operations.

        Args:
            memory_dir: The memory directory path

        Returns:
            A canUseTool function
        """
        FILE_READ_TOOL_NAME = "FileRead"
        GREP_TOOL_NAME = "Grep"
        GLOB_TOOL_NAME = "Glob"
        BASH_TOOL_NAME = "Bash"
        FILE_EDIT_TOOL_NAME = "FileEdit"
        FILE_WRITE_TOOL_NAME = "FileWrite"

        def can_use_tool(tool: Any, input_data: Dict[str, Any]) -> Dict[str, Any]:
            tool_name = getattr(tool, 'name', str(tool))

            if tool_name == FILE_READ_TOOL_NAME:
                return {"behavior": "allow", "updated_input": input_data}

            if tool_name == GREP_TOOL_NAME:
                return {"behavior": "allow", "updated_input": input_data}

            if tool_name == GLOB_TOOL_NAME:
                return {"behavior": "allow", "updated_input": input_data}

            if tool_name == BASH_TOOL_NAME:
                return {"behavior": "allow", "updated_input": input_data}

            if tool_name in (FILE_EDIT_TOOL_NAME, FILE_WRITE_TOOL_NAME):
                file_path = input_data.get("file_path", "")
                if isinstance(file_path, str) and memory_dir in file_path:
                    return {"behavior": "allow", "updated_input": input_data}
                return {
                    "behavior": "deny",
                    "message": f"Only file operations within {memory_dir} are permitted",
                    "decision_reason": {"type": "other", "reason": "path outside memory dir"},
                }

            return {
                "behavior": "deny",
                "message": f"Tool {tool_name} is not permitted in memory extraction context",
                "decision_reason": {"type": "other", "reason": "tool not allowed"},
            }

        return can_use_tool


def is_model_visible_message(message: Dict[str, Any]) -> bool:
    """
    Check if a message is visible to the model.

    Args:
        message: Message dictionary

    Returns:
        True if the message type is 'user' or 'assistant'
    """
    return message.get("type") in ("user", "assistant")


def count_model_visible_messages_since(
    messages: List[Dict[str, Any]],
    since_uuid: Optional[str],
) -> int:
    """
    Count model-visible messages since a given UUID.

    Args:
        messages: List of message dictionaries
        since_uuid: Optional UUID to count from

    Returns:
        Number of visible messages
    """
    if since_uuid is None:
        return sum(1 for m in messages if is_model_visible_message(m))

    found_start = False
    count = 0
    for message in messages:
        if not found_start:
            if message.get("uuid") == since_uuid:
                found_start = True
            continue
        if is_model_visible_message(message):
            count += 1

    if not found_start:
        return sum(1 for m in messages if is_model_visible_message(m))

    return count


def extract_written_paths(agent_messages: List[Dict[str, Any]]) -> List[str]:
    """
    Extract file paths from agent messages.

    Args:
        agent_messages: List of agent message dictionaries

    Returns:
        List of extracted file paths
    """
    paths: List[str] = []
    FILE_EDIT_TOOL_NAME = "FileEdit"
    FILE_WRITE_TOOL_NAME = "FileWrite"

    for message in agent_messages:
        if message.get("type") != "assistant":
            continue

        content = message.get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if block.get("type") != "tool_use":
                continue

            tool_name = block.get("name")
            if tool_name not in (FILE_EDIT_TOOL_NAME, FILE_WRITE_TOOL_NAME):
                continue

            tool_input = block.get("input", {})
            if isinstance(tool_input, dict):
                file_path = tool_input.get("file_path")
                if isinstance(file_path, str):
                    paths.append(file_path)

    return list(set(paths))
