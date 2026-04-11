"""
Memory extraction module.
Extracts memories from conversations and messages.
"""
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .memory_classifier import MemoryClassifier
from .memory_analyzer import MemoryAnalyzer, MemoryAnalysisResult


@dataclass
class ExtractedMemory:
    id: str
    memory_type: str
    content: str
    importance: float
    source_session: Optional[str] = None
    source_message_idx: Optional[int] = None
    createdAt: int = 0
    tags: list[str] = field(default_factory=list)
    priority: str = "medium"
    categories: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.createdAt == 0:
            self.createdAt = int(datetime.utcnow().timestamp() * 1000)

    def to_dict(self) -> dict:
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
        }


@dataclass
class ExtractionResult:
    memories: list[ExtractedMemory]
    analysis: Optional[MemoryAnalysisResult] = None
    extraction_time_ms: int = 0
    messages_processed: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "memories": [m.to_dict() for m in self.memories],
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "extraction_time_ms": self.extraction_time_ms,
            "messages_processed": self.messages_processed,
            "errors": self.errors,
        }


class MemoryExtractor:
    """
    Extracts memories from conversations and messages.
    """

    def __init__(self):
        self._classifier = MemoryClassifier()
        self._analyzer = MemoryAnalyzer()

    def extract_memories_from_conversation(
        self,
        messages: list[dict],
        session_id: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> ExtractionResult:
        """
        Extract memories from a conversation.
        
        Args:
            messages: List of message dictionaries
            session_id: Optional session identifier
            config: Optional extraction configuration
            
        Returns:
            ExtractionResult with extracted memories
        """
        if config is None:
            config = {}

        min_importance = config.get("min_importance", 0.5)
        max_memories = config.get("max_memories", 20)

        start_time = datetime.utcnow()
        memories: list[ExtractedMemory] = []
        errors: list[str] = []

        for idx, message in enumerate(messages):
            try:
                content = message.get("content", "")
                if not content or len(content.strip()) < 10:
                    continue

                message_memories = self.extract_memories_from_message(
                    content=content,
                    session_id=session_id,
                    message_idx=idx,
                )

                for mem in message_memories:
                    if mem.importance >= min_importance:
                        memories.append(mem)

            except Exception as e:
                errors.append(f"Error processing message {idx}: {str(e)}")

        memories = self._rank_memories(memories)

        memories = memories[:max_memories]

        analysis = self._analyzer.analyze_memory_relevance(
            "\n".join(m.content for m in memories),
            project_context=config.get("project_context"),
        )

        end_time = datetime.utcnow()
        extraction_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return ExtractionResult(
            memories=memories,
            analysis=analysis,
            extraction_time_ms=extraction_time_ms,
            messages_processed=len(messages),
            errors=errors,
        )

    def extract_memories_from_message(
        self,
        content: str,
        session_id: Optional[str] = None,
        message_idx: Optional[int] = None,
    ) -> list[ExtractedMemory]:
        """
        Extract memories from a single message.
        
        Args:
            content: Message content
            session_id: Optional session identifier
            message_idx: Optional message index
            
        Returns:
            List of extracted memories
        """
        memories: list[ExtractedMemory] = []
        timestamp = int(datetime.utcnow().timestamp() * 1000)

        facts = self._extract_facts(content)
        for fact in facts:
            memory_type = self._classifier.suggest_memory_type(fact)
            classification = self._classifier.classify(fact, memory_type)

            memories.append(ExtractedMemory(
                id=self._generate_memory_id(fact, "fact"),
                memory_type=memory_type,
                content=fact.strip(),
                importance=self._calculate_importance(fact),
                source_session=session_id,
                source_message_idx=message_idx,
                createdAt=timestamp,
                tags=classification.tags,
                priority=classification.priority.value,
                categories=[classification.primary_category.value] +
                           [c.value for c in classification.secondary_categories],
            ))

        decisions = self._extract_decisions(content)
        for decision in decisions:
            memory_type = "decision"
            classification = self._classifier.classify(decision, memory_type)

            memories.append(ExtractedMemory(
                id=self._generate_memory_id(decision, "decision"),
                memory_type=memory_type,
                content=decision.strip(),
                importance=self._calculate_importance(decision),
                source_session=session_id,
                source_message_idx=message_idx,
                createdAt=timestamp,
                tags=classification.tags,
                priority=classification.priority.value,
                categories=[classification.primary_category.value],
            ))

        preferences = self._extract_preferences(content)
        for pref in preferences:
            memory_type = "preference"
            classification = self._classifier.classify(pref, memory_type)

            memories.append(ExtractedMemory(
                id=self._generate_memory_id(pref, "pref"),
                memory_type=memory_type,
                content=pref.strip(),
                importance=self._calculate_importance(pref),
                source_session=session_id,
                source_message_idx=message_idx,
                createdAt=timestamp,
                tags=classification.tags,
                priority=classification.priority.value,
                categories=[classification.primary_category.value],
            ))

        return memories

    def _extract_facts(self, text: str) -> list[str]:
        """Extract factual statements from text."""
        facts = []
        patterns = [
            r"(?:uses?|using|used)\s+[^.]+",
            r"(?:is\s+a?|is\s+an)\s+[^.]+",
            r"(?:has\s+been\s+)?configured\s+as\s+[^.]+",
            r"(?:database|server|api|endpoint)\s+[^.]+",
            r"(?:file|path|directory)\s+[^.]+",
            r"(?:set\s+up\s+|established\s+)[^.]+",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            facts.extend(matches[:3])
        return facts[:5]

    def _extract_decisions(self, text: str) -> list[str]:
        """Extract decision statements from text."""
        decisions = []
        patterns = [
            r"(?:decided|chose|selected|agreed)\s+to\s+[^.]+",
            r"(?:will|going\s+to|plan\s+to)\s+[^.]+",
            r"(?:implementing|building|creating)\s+[^.]+",
            r"(?:use|adopt|apply)\s+[^.]+",
            r"(?:going\s+with|opted\s+for)\s+[^.]+",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            decisions.extend(matches[:3])
        return decisions[:5]

    def _extract_preferences(self, text: str) -> list[str]:
        """Extract preference statements from text."""
        prefs = []
        patterns = [
            r"(?:I\s+prefer|I\s+like\s+better|I\s+enjoy)\s+[^.]+",
            r"(?:I\s+don't\s+like|I\s+dislike|I\s+avoid)\s+[^.]+",
            r"(?:my\s+favorite|I\s+love)\s+[^.]+",
            r"(?:best|worst|ideal)\s+[^.]+",
            r"(?:I\s+always|I\s+never|I\s+usually)\s+[^.]+",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            prefs.extend(matches[:3])
        return prefs[:5]

    def classify_memory(self, content: str) -> str:
        """
        Classify the memory type.
        
        Args:
            content: Memory content
            
        Returns:
            Memory type string
        """
        return self._classifier.suggest_memory_type(content)

    def rank_memories(
        self,
        memories: list[ExtractedMemory],
    ) -> list[ExtractedMemory]:
        """
        Rank memories by importance.
        
        Args:
            memories: List of memories to rank
            
        Returns:
            Sorted list of memories
        """
        return self._rank_memories(memories)

    def _rank_memories(
        self,
        memories: list[ExtractedMemory],
    ) -> list[ExtractedMemory]:
        """Internal ranking logic."""
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        def memory_sort_key(mem: ExtractedMemory) -> tuple:
            priority = priority_order.get(mem.priority, 2)
            importance = mem.importance
            return (priority, -importance)

        return sorted(memories, key=memory_sort_key)

    def _calculate_importance(self, text: str) -> float:
        """Calculate importance score for text."""
        importance = 0.5
        important_keywords = [
            "remember", "important", "must", "need", "preference",
            "decision", "configured", "established", "critical",
            "security", "password", "secret", "key",
        ]
        for kw in important_keywords:
            if kw.lower() in text.lower():
                importance += 0.1

        return min(importance, 1.0)

    def _generate_memory_id(self, content: str, prefix: str) -> str:
        """Generate a unique memory ID."""
        hash_input = f"{content[:50]}_{datetime.utcnow().timestamp()}"
        hash_suffix = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        return f"{prefix}_{hash_suffix}"
