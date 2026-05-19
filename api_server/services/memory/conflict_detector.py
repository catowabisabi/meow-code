import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class ConflictType(Enum):
    SEMANTIC_SIMILARITY = "semantic_similarity"
    TEMPORAL_OVERLAP = "temporal_overlap"
    ENTITY_CONTRADICTION = "entity_contradiction"
    DUPLICATE = "duplicate"

@dataclass
class MemoryConflict:
    conflict_type: ConflictType
    existing_memory_id: str
    new_memory_id: str
    similarity_score: float
    overlap_info: Optional[Dict[str, Any]] = None
    resolution_suggestion: Optional[str] = None

@dataclass
class ConflictReport:
    has_conflicts: bool
    conflicts: List[MemoryConflict]
    resolved_automatically: int
    requires_manual_resolution: int

class ConflictDetector:
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        temporal_window_seconds: float = 3600.0,
    ):
        self._similarity_threshold = similarity_threshold
        self._temporal_window = temporal_window_seconds
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    async def check_conflicts(
        self,
        new_memory: Dict[str, Any],
        user_id: str,
        existing_memories: List[Dict[str, Any]],
    ) -> ConflictReport:
        conflicts: List[MemoryConflict] = []
        auto_resolved = 0

        for existing in existing_memories:
            if existing.get("metadata", {}).get("user_id") != user_id:
                continue

            conflict = await self._detect_conflict(new_memory, existing)
            if conflict:
                conflicts.append(conflict)

                if self._can_auto_resolve(conflict):
                    auto_resolved += 1

        return ConflictReport(
            has_conflicts=len(conflicts) > 0,
            conflicts=conflicts,
            resolved_automatically=auto_resolved,
            requires_manual_resolution=len(conflicts) - auto_resolved,
        )

    async def _detect_conflict(
        self,
        new_memory: Dict[str, Any],
        existing_memory: Dict[str, Any],
    ) -> Optional[MemoryConflict]:
        if new_memory.get("id") == existing_memory.get("id"):
            return None

        similarity = await self._calculate_similarity(
            new_memory.get("document", ""),
            existing_memory.get("document", ""),
        )

        if similarity >= self._similarity_threshold:
            return MemoryConflict(
                conflict_type=ConflictType.SEMANTIC_SIMILARITY,
                existing_memory_id=existing_memory.get("id", ""),
                new_memory_id=new_memory.get("id", ""),
                similarity_score=similarity,
                resolution_suggestion="merge" if similarity >= 0.95 else "review",
            )

        temporal_conflict = self._check_temporal_overlap(
            new_memory,
            existing_memory,
        )
        if temporal_conflict:
            return temporal_conflict

        entity_conflict = self._check_entity_contradiction(
            new_memory,
            existing_memory,
        )
        if entity_conflict:
            return entity_conflict

        return None

    async def _calculate_similarity(
        self,
        text1: str,
        text2: str,
    ) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def _check_temporal_overlap(
        self,
        new_memory: Dict[str, Any],
        existing_memory: Dict[str, Any],
    ) -> Optional[MemoryConflict]:
        new_time = new_memory.get("created_at", time.time())
        existing_time = existing_memory.get("created_at", 0)

        time_diff = abs(new_time - existing_time)

        if time_diff < self._temporal_window:
            new_entities = set(
                new_memory.get("metadata", {}).get("entities", [])
            )
            existing_entities = set(
                existing_memory.get("metadata", {}).get("entities", [])
            )

            common_entities = new_entities & existing_entities
            if common_entities:
                return MemoryConflict(
                    conflict_type=ConflictType.TEMPORAL_OVERLAP,
                    existing_memory_id=existing_memory.get("id", ""),
                    new_memory_id=new_memory.get("id", ""),
                    similarity_score=len(common_entities) / max(len(new_entities | existing_entities), 1),
                    overlap_info={
                        "time_diff_seconds": time_diff,
                        "common_entities": list(common_entities),
                    },
                    resolution_suggestion="timestamp_order",
                )

        return None

    def _check_entity_contradiction(
        self,
        new_memory: Dict[str, Any],
        existing_memory: Dict[str, Any],
    ) -> Optional[MemoryConflict]:
        new_entities = set(
            new_memory.get("metadata", {}).get("entities", [])
        )
        existing_entities = set(
            existing_memory.get("metadata", {}).get("entities", [])
        )

        common = new_entities & existing_entities

        if len(common) >= 3:
            content1 = new_memory.get("document", "").lower()
            content2 = existing_memory.get("document", "").lower()

            negation_words = {"not", "no", "never", "don't", "doesn't", "didn't", "won't", "wouldn't"}
            has_negation1 = any(f" {w} " in f" {content1} " for w in negation_words)
            has_negation2 = any(f" {w} " in f" {content2} " for w in negation_words)

            if has_negation1 != has_negation2:
                return MemoryConflict(
                    conflict_type=ConflictType.ENTITY_CONTRADICTION,
                    existing_memory_id=existing_memory.get("id", ""),
                    new_memory_id=new_memory.get("id", ""),
                    similarity_score=len(common) / max(len(new_entities | existing_entities), 1),
                    overlap_info={
                        "contradicting_entities": list(common),
                    },
                    resolution_suggestion="manual_review",
                )

        return None

    def _can_auto_resolve(self, conflict: MemoryConflict) -> bool:
        if conflict.conflict_type == ConflictType.DUPLICATE:
            return True
        if conflict.conflict_type == ConflictType.SEMANTIC_SIMILARITY:
            return conflict.similarity_score >= 0.95
        return False

    async def merge_memories(
        self,
        memory1_id: str,
        memory2_id: str,
    ) -> Dict[str, Any]:
        mem1 = self._memory_cache.get(memory1_id, {})
        mem2 = self._memory_cache.get(memory2_id, {})

        merged = {
            "id": memory1_id,
            "document": mem1.get("document", "") + "\n" + mem2.get("document", ""),
            "metadata": {
                **mem1.get("metadata", {}),
                **mem2.get("metadata", {}),
                "merged_from": [memory1_id, memory2_id],
                "merged_at": time.time(),
            },
        }

        return merged

_conflict_detector: Optional[ConflictDetector] = None

def get_conflict_detector() -> ConflictDetector:
    global _conflict_detector
    if _conflict_detector is None:
        _conflict_detector = ConflictDetector()
    return _conflict_detector