"""
Memory analysis module.
Analyzes memories for relevance, relationships, and conflicts.
"""
import re
from dataclasses import dataclass, field
from typing import Optional



@dataclass
class MemoryRelevance:
    memory_id: str
    relevance_score: float
    reasoning: str


@dataclass
class MemoryRelationship:
    source_id: str
    target_id: str
    relationship_type: str
    description: str


@dataclass
class MemoryConflict:
    memory_a_id: str
    memory_b_id: str
    description: str


@dataclass
class MemoryMerge:
    memory_ids: list[str]
    merged_content: str


@dataclass
class MemoryAnalysisResult:
    relevance_scores: dict[str, float] = field(default_factory=dict)
    relationships: list[MemoryRelationship] = field(default_factory=list)
    conflicts: list[MemoryConflict] = field(default_factory=list)
    suggested_merges: list[MemoryMerge] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "relevance_scores": self.relevance_scores,
            "relationships": [
                {
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "relationship_type": r.relationship_type,
                    "description": r.description,
                }
                for r in self.relationships
            ],
            "conflicts": [
                {
                    "memory_a": c.memory_a_id,
                    "memory_b": c.memory_b_id,
                    "description": c.description,
                }
                for c in self.conflicts
            ],
            "suggested_merges": [
                {"ids": m.memory_ids, "merged_content": m.merged_content}
                for m in self.suggested_merges
            ],
        }


@dataclass
class MemorySummary:
    total_memories: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
    high_priority_memories: list[str]
    recent_memories: list[str]


class MemoryAnalyzer:
    """
    Analyzes memories for relevance, relationships, and conflicts.
    """

    def analyze_memory_relevance(
        self,
        memory_content: str,
        project_context: Optional[str] = None,
    ) -> float:
        """
        Analyze the relevance of a memory to the current context.
        
        Args:
            memory_content: The memory content to analyze
            project_context: Optional project context
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not project_context:
            return 0.5

        content_lower = memory_content.lower()
        context_lower = project_context.lower()

        context_words = set(context_lower.split())
        content_words = set(content_lower.split())

        common_words = context_words & content_words
        relevance = len(common_words) / max(len(context_words), 1)

        topic_keywords = ["project", "codebase", "feature", "bug", "api"]
        for keyword in topic_keywords:
            if keyword in content_lower and keyword in context_lower:
                relevance += 0.1

        return min(relevance, 1.0)

    def analyze_memory_relationships(
        self,
        memories: list[dict],
    ) -> list[MemoryRelationship]:
        """
        Find relationships between memories.
        
        Args:
            memories: List of memory dictionaries
            
        Returns:
            List of MemoryRelationship objects
        """
        relationships: list[MemoryRelationship] = []
        seen_pairs: set[tuple[str, str]] = set()

        for i, mem_a in enumerate(memories):
            for mem_b in memories[i + 1:]:
                mem_a_id = mem_a.get("id", f"memory_{i}")
                mem_b_id = mem_b.get("id", f"memory_{i + 1}")

                pair_key = tuple(sorted([mem_a_id, mem_b_id]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                relationship = self._find_relationship(mem_a, mem_b)
                if relationship:
                    relationships.append(relationship)

        return relationships

    def _find_relationship(
        self,
        mem_a: dict,
        mem_b: dict,
    ) -> Optional[MemoryRelationship]:
        """Find relationship between two memories."""
        content_a = mem_a.get("content", "").lower()
        content_b = mem_b.get("content", "").lower()

        temporal_patterns = [
            (r"\b(before|earlier|previously)\b", r"\b(after|later|now)\b"),
            (r"\b(first|initially)\b", r"\b(then|next|finally)\b"),
        ]

        for pattern_a, pattern_b in temporal_patterns:
            if re.search(pattern_a, content_a) and re.search(pattern_b, content_b):
                return MemoryRelationship(
                    source_id=mem_a.get("id", ""),
                    target_id=mem_b.get("id", ""),
                    relationship_type="temporal",
                    description="Temporal sequence relationship",
                )

        common_words = set(content_a.split()) & set(content_b.split())
        significant_overlap = len(common_words) > 3

        if significant_overlap:
            overlap_str = ", ".join(list(common_words)[:5])
            return MemoryRelationship(
                source_id=mem_a.get("id", ""),
                target_id=mem_b.get("id", ""),
                relationship_type="semantic",
                description=f"Shared concepts: {overlap_str}",
            )

        action_words_a = re.findall(r"\b(uses?|uses?|created?|built?|implemented?)\b", content_a)
        action_words_b = re.findall(r"\b(uses?|uses?|created?|built?|implemented?)\b", content_b)

        if action_words_a and action_words_b:
            if any(word in content_b for word in ["because", "therefore", "using"]):
                return MemoryRelationship(
                    source_id=mem_a.get("id", ""),
                    target_id=mem_b.get("id", ""),
                    relationship_type="causal",
                    description="Causal relationship detected",
                )

        return None

    def find_memory_conflicts(
        self,
        memories: list[dict],
    ) -> list[MemoryConflict]:
        """
        Find conflicting memories.
        
        Args:
            memories: List of memory dictionaries
            
        Returns:
            List of MemoryConflict objects
        """
        conflicts: list[MemoryConflict] = []

        contradiction_pairs = [
            ("use ", "don't use "),
            ("use ", "avoid "),
            ("prefer ", "dislike "),
            ("always ", "never "),
            ("need ", "don't need "),
            ("is ", "is not "),
            ("was ", "wasn't "),
        ]

        for i, mem_a in enumerate(memories):
            for mem_b in memories[i + 1:]:
                content_a = mem_a.get("content", "").lower()
                content_b = mem_b.get("content", "").lower()

                for pos, neg in contradiction_pairs:
                    has_pos_a = pos in content_a and neg not in content_a
                    has_neg_b = neg in content_b and pos not in content_b
                    has_pos_b = pos in content_b and neg not in content_b
                    has_neg_a = neg in content_a and pos not in content_a

                    if (has_pos_a and has_neg_b) or (has_pos_b and has_neg_a):
                        conflicts.append(MemoryConflict(
                            memory_a_id=mem_a.get("id", f"memory_{i}"),
                            memory_b_id=mem_b.get("id", f"memory_{i + 1}"),
                            description=f"Contradiction: '{pos}' vs '{neg}'",
                        ))
                        break

        return conflicts

    def get_memory_summary(
        self,
        memories: list[dict],
    ) -> MemorySummary:
        """
        Generate a summary of memories.
        
        Args:
            memories: List of memory dictionaries
            
        Returns:
            MemorySummary object
        """
        by_category: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        high_priority_ids: list[str] = []
        recent_ids: list[str] = []

        for mem in memories:
            mem_type = mem.get("type", "context")
            by_category[mem_type] = by_category.get(mem_type, 0) + 1

            priority = mem.get("priority", "medium")
            by_priority[priority] = by_priority.get(priority, 0) + 1

            if priority in ("critical", "high"):
                mem_id = mem.get("id", "")
                if mem_id:
                    high_priority_ids.append(mem_id)

            created_at = mem.get("createdAt", 0)
            if created_at > 0:
                recent_ids.append(mem.get("id", ""))

        recent_ids.sort(key=lambda x: memories[[m.get("id", "") for m in memories].index(x)].get("createdAt", 0) if x in [m.get("id", "") for m in memories] else 0, reverse=True)

        return MemorySummary(
            total_memories=len(memories),
            by_category=by_category,
            by_priority=by_priority,
            high_priority_memories=high_priority_ids[:5],
            recent_memories=recent_ids[:10],
        )

    def calculate_similarity(
        self,
        content_a: str,
        content_b: str,
    ) -> float:
        """
        Calculate similarity between two memory contents.
        
        Args:
            content_a: First memory content
            content_b: Second memory content
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        words_a = set(content_a.lower().split())
        words_b = set(content_b.lower().split())

        if not words_a or not words_b:
            return 0.0

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        return intersection / union if union > 0 else 0.0

    def suggest_merges(
        self,
        memories: list[dict],
        similarity_threshold: float = 0.7,
    ) -> list[MemoryMerge]:
        """
        Suggest memory merges for similar memories.
        
        Args:
            memories: List of memory dictionaries
            similarity_threshold: Minimum similarity to suggest merge
            
        Returns:
            List of MemoryMerge suggestions
        """
        merges: list[MemoryMerge] = []
        used_ids: set[str] = set()

        for i, mem_a in enumerate(memories):
            if mem_a.get("id", f"memory_{i}") in used_ids:
                continue

            similar: list[tuple[int, float]] = []
            for j, mem_b in enumerate(memories[i + 1:], start=i + 1):
                if mem_b.get("id", f"memory_{j}") in used_ids:
                    continue

                similarity = self.calculate_similarity(
                    mem_a.get("content", ""),
                    mem_b.get("content", ""),
                )
                if similarity >= similarity_threshold:
                    similar.append((j, similarity))

            if similar:
                ids_to_merge = [mem_a.get("id", f"memory_{i}")]
                for j, _ in similar:
                    ids_to_merge.append(memories[j].get("id", f"memory_{j}"))
                    used_ids.add(memories[j].get("id", f"memory_{j}"))

                used_ids.add(mem_a.get("id", f"memory_{i}"))

                merged_content = self._merge_content(
                    [mem_a.get("content", "")] +
                    [memories[j].get("content", "") for j, _ in similar]
                )

                merges.append(MemoryMerge(
                    memory_ids=ids_to_merge,
                    merged_content=merged_content,
                ))

        return merges

    def _merge_content(self, contents: list[str]) -> str:
        """Merge multiple content strings into one."""
        if not contents:
            return ""

        if len(contents) == 1:
            return contents[0]

        sentences: list[str] = []
        for content in contents:
            parts = content.split(". ")
            sentences.extend([p.strip() for p in parts if p.strip()])

        unique_sentences = list(dict.fromkeys(sentences))

        return ". ".join(unique_sentences) + "."
