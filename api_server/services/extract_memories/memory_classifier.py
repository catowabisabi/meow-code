"""
Memory classification module.
Classifies memories into categories and determines priority levels.
"""
import re
from enum import Enum
from typing import Optional
from .prompts import ExtractionPrompts


class MemoryCategory(str, Enum):
    PROJECT = "project"
    PERSONAL = "personal"
    WORK = "work"
    TECHNICAL = "technical"
    CONTEXT = "context"


class MemoryPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ClassificationResult:
    def __init__(
        self,
        primary_category: MemoryCategory,
        secondary_categories: list[MemoryCategory],
        tags: list[str],
        priority: MemoryPriority,
        expires_at: Optional[int] = None,
        confidence: float = 0.5,
    ):
        self.primary_category = primary_category
        self.secondary_categories = secondary_categories
        self.tags = tags
        self.priority = priority
        self.expires_at = expires_at
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "primary_category": self.primary_category.value,
            "secondary_categories": [c.value for c in self.secondary_categories],
            "tags": self.tags,
            "priority": self.priority.value,
            "expires_at": self.expires_at,
            "confidence": self.confidence,
        }


class MemoryClassifier:
    """
    Classifies memories into categories and determines their priority.
    """

    def __init__(self):
        self._patterns = ExtractionPrompts.get_memory_type_patterns()

    def classify(self, content: str, suggested_type: Optional[str] = None) -> ClassificationResult:
        """
        Classify a memory into categories and priority.
        
        Args:
            content: The memory content to classify
            suggested_type: Optional type suggestion from extraction
            
        Returns:
            ClassificationResult with category, tags, and priority
        """
        content_lower = content.lower()

        category_scores: dict[MemoryCategory, float] = {
            MemoryCategory.PROJECT: 0.0,
            MemoryCategory.PERSONAL: 0.0,
            MemoryCategory.WORK: 0.0,
            MemoryCategory.TECHNICAL: 0.0,
            MemoryCategory.CONTEXT: 0.0,
        }

        for category, patterns in self._patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    category_scores[MemoryCategory(category)] += 1.0

        if suggested_type:
            type_map = {
                "fact": MemoryCategory.TECHNICAL,
                "decision": MemoryCategory.PROJECT,
                "preference": MemoryCategory.PERSONAL,
                "context": MemoryCategory.CONTEXT,
            }
            if suggested_type in type_map:
                category_scores[type_map[suggested_type]] += 2.0

        sorted_categories = sorted(
            category_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        primary = sorted_categories[0][0] if sorted_categories[0][1] > 0 else MemoryCategory.CONTEXT
        secondary: list[MemoryCategory] = []
        for cat, score in sorted_categories[1:]:
            if score > 0:
                secondary.append(cat)

        priority = self._determine_priority(content, primary)
        tags = self._extract_tags(content, primary)
        confidence = min(sorted_categories[0][1] / 3.0, 1.0) if sorted_categories[0][1] > 0 else 0.5

        return ClassificationResult(
            primary_category=primary,
            secondary_categories=secondary[:3],
            tags=tags,
            priority=priority,
            expires_at=None,
            confidence=confidence,
        )

    def _determine_priority(
        self,
        content: str,
        category: MemoryCategory,
    ) -> MemoryPriority:
        """Determine the priority level based on content and category."""
        content_lower = content.lower()

        critical_keywords = [
            "security", "password", "secret", "key", "credential",
            "critical", "urgent", "asap", "must", "required",
        ]
        high_keywords = [
            "important", "decision", "agreed", "decided", "chosen",
            "preference", "always", "never", "best", "worst",
        ]
        low_keywords = [
            "maybe", "perhaps", "might", "could", "sometimes",
            "usually", "normally", "generally", "typically",
        ]

        for kw in critical_keywords:
            if kw in content_lower:
                return MemoryPriority.CRITICAL

        for kw in high_keywords:
            if kw in content_lower:
                return MemoryPriority.HIGH

        if category == MemoryCategory.PERSONAL:
            return MemoryPriority.MEDIUM

        for kw in low_keywords:
            if kw in content_lower:
                return MemoryPriority.LOW

        return MemoryPriority.MEDIUM

    def _extract_tags(self, content: str, category: MemoryCategory) -> list[str]:
        """Extract relevant tags from the content."""
        tags = [category.value]

        content_lower = content.lower()

        tech_tags = ["api", "database", "function", "class", "module"]
        for tag in tech_tags:
            if tag in content_lower:
                tags.append(tag)

        framework_match = re.search(
            r"(react|angular|vue|django|flask|express|fastapi|spring)",
            content_lower
        )
        if framework_match:
            tags.append(framework_match.group(1))

        language_match = re.search(
            r"\b(python|javascript|typescript|java|cpp|c#|go|rust|ruby)\b",
            content_lower
        )
        if language_match:
            tags.append(language_match.group(1))

        if "prefer" in content_lower or "like" in content_lower:
            tags.append("preference")

        if "decide" in content_lower or "agreed" in content_lower:
            tags.append("decision")

        return list(set(tags))[:5]

    def get_memory_tags(
        self,
        content: str,
        memory_type: Optional[str] = None,
    ) -> list[str]:
        """
        Get tags for a memory.
        
        Args:
            content: The memory content
            memory_type: Optional memory type hint
            
        Returns:
            List of relevant tags
        """
        result = self.classify(content, memory_type)
        return result.tags

    def get_memory_priority(
        self,
        content: str,
        memory_type: Optional[str] = None,
        importance: float = 0.5,
    ) -> MemoryPriority:
        """
        Determine the priority level for a memory.
        
        Args:
            content: The memory content
            memory_type: Optional memory type hint
            importance: Optional importance score from extraction
            
        Returns:
            MemoryPriority level
        """
        result = self.classify(content, memory_type)

        if importance > 0.8:
            if result.priority != MemoryPriority.CRITICAL:
                return MemoryPriority.HIGH
        elif importance < 0.4:
            if result.priority == MemoryPriority.HIGH:
                return MemoryPriority.MEDIUM

        return result.priority

    def suggest_memory_type(self, content: str) -> str:
        """
        Suggest the memory type based on content patterns.
        
        Args:
            content: The memory content
            
        Returns:
            Suggested memory type string
        """
        content_lower = content.lower()

        decision_patterns = [
            r"\b(decide|chose|selected|agreed|will use|going with)\b",
            r"\b(prefer|preferred|like better|favor)\b",
        ]
        for pattern in decision_patterns:
            if re.search(pattern, content_lower):
                return "decision"

        preference_patterns = [
            r"\b(prefer|like|love|hate|dislike|enjoy|want|need)\b",
            r"\b(always|never|usually|typically)\b",
        ]
        for pattern in preference_patterns:
            if re.search(pattern, content_lower):
                return "preference"

        fact_patterns = [
            r"\b(uses?|using|is a|was|are|have|has)\b",
            r"\b(database|api|server|client|file|path)\b",
        ]
        for pattern in fact_patterns:
            if re.search(pattern, content_lower):
                return "fact"

        return "context"

    def is_high_priority_memory(self, content: str) -> bool:
        """
        Quick check if memory is high priority.
        
        Args:
            content: The memory content
            
        Returns:
            True if high priority
        """
        priority = self.get_memory_priority(content)
        return priority in (MemoryPriority.CRITICAL, MemoryPriority.HIGH)
