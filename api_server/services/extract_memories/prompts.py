"""
Extraction prompts for memory extraction service.
Provides prompts for extracting, analyzing, and classifying memories from conversations.
"""
from typing import Optional, List


MEMORY_TYPE_PATTERNS = {
    "project": [
        "project", "codebase", "repository", "repo", "implementation",
        "feature", "bug", "issue", "task", "requirement", "specification",
    ],
    "personal": [
        "i prefer", "i like", "i hate", "i want", "i need", "my preference",
        "i always", "i never", "i usually", "i enjoy", "i dislike",
    ],
    "work": [
        "deadline", "meeting", "sprint", "standup", "review", "approval",
        "manager", "team lead", "stakeholder", "client", "deliverable",
    ],
    "technical": [
        "api", "database", "schema", "endpoint", "function", "class",
        "module", "package", "library", "framework", "dependency",
        "configuration", "deploy", "build", "test", "ci", "cd",
    ],
    "context": [
        "context", "background", "situation", "circumstance", "前提",
        "previously", "earlier", "before", "remember", "noted",
    ],
}


EXTRACTION_PROMPT_TEMPLATE = """You are a memory extraction specialist. Your task is to identify and extract durable memories from the conversation above that should be saved for future reference.

MEMORY TYPES TO EXTRACT:
- **facts**: Factual information, knowledge, or discoveries (e.g., "uses PostgreSQL database", "API endpoint is /api/v1/users")
- **decisions**: Decisions made, choices selected, or agreements reached (e.g., "decided to use React for frontend", "agreed on REST API")
- **preferences**: User preferences, likes, dislikes, or work style (e.g., "prefers dark mode", "likes detailed documentation")
- **context**: Important context or background information (e.g., "working on authentication feature", "team is remote")

EXISTING MEMORIES (for context and avoiding duplicates):
{existing_memories}

NEW MESSAGE COUNT: {message_count}

EXTRACTION RULES:
1. Only extract memories that are non-obvious and provide lasting value
2. Avoid duplicating existing memories - check the manifest above
3. Focus on specific, actionable information over general statements
4. Prefer exact quotes or close paraphrases from the conversation
5. Rate importance: 0.0-1.0 (higher = more important to remember)
6. Maximum 5 memories per extraction run

OUTPUT FORMAT:
For each memory, provide:
- type: one of [fact, decision, preference, context]
- content: the memory content (concise, 1-2 sentences max)
- importance: 0.0-1.0 rating
- tags: relevant tags for categorization

Example output:
```json
[
  {{
    "type": "decision",
    "content": "Chose TypeScript over JavaScript for type safety",
    "importance": 0.85,
    "tags": ["language", "typescript", "decision"]
  }}
]
```

Begin extraction now. Focus only on genuinely useful memories that would help future sessions understand this project and user."""


ANALYSIS_PROMPT_TEMPLATE = """Analyze the following extracted memories for relevance, relationships, and potential conflicts.

MEMORIES TO ANALYZE:
{memories}

RELATED EXISTING MEMORIES:
{related_memories}

ANALYSIS TASKS:
1. **Relevance Analysis**: Assess how relevant each memory is to the current project/context
2. **Relationship Finding**: Identify connections between memories (causal, temporal, semantic)
3. **Conflict Detection**: Find any contradictory or conflicting information
4. **Deduplication**: Suggest merging of duplicate or highly similar memories

OUTPUT FORMAT:
```json
{{
  "relevance_scores": {{
    "<memory_id>": <0.0-1.0 relevance score>
  }},
  "relationships": [
    {{
      "source_id": "<memory_id>",
      "target_id": "<memory_id>",
      "relationship_type": "causal|temporal|semantic|contradicts",
      "description": "Brief description of the relationship"
    }}
  ],
  "conflicts": [
    {{
      "memory_a": "<memory_id>",
      "memory_b": "<memory_id>",
      "description": "Description of the conflict"
    }}
  ],
  "suggested_merges": [
    {{
      "ids": ["<memory_id>", "<memory_id>"],
      "merged_content": "Proposed merged content"
    }}
  ]
}}
```

Provide your analysis now."""


CLASSIFICATION_PROMPT_TEMPLATE = """Classify the following memory into categories and determine its priority.

MEMORY TO CLASSIFY:
{content}

MEMORY TYPE: {memory_type}
IMPORTANCE: {importance}

CLASSIFICATION TASKS:
1. **Category Classification**: Determine the primary and secondary categories
2. **Tag Generation**: Generate relevant tags for this memory
3. **Priority Determination**: Determine the priority level (critical, high, medium, low)
4. **Expiry Assessment**: Estimate if/when this memory might become outdated

CATEGORIES:
- project: Related to the current project or codebase
- personal: User's personal preferences or work style
- work: Work-related items like deadlines, meetings, team info
- technical: Technical decisions, patterns, or specifications
- context: Background context or situation description

PRIORITY LEVELS:
- critical: Must remember, will cause significant issues if lost (e.g., critical decisions, security info)
- high: Very important, would be helpful to remember (e.g., key preferences, major decisions)
- medium: Moderately useful, nice to remember (e.g., general preferences, context)
- low: Minor importance, low priority to preserve (e.g., casual mentions, temporary info)

OUTPUT FORMAT:
```json
{{
  "primary_category": "<category>",
  "secondary_categories": ["<category>", "<category>"],
  "tags": ["<tag1>", "<tag2>", "<tag3>"],
  "priority": "<critical|high|medium|low>",
  "expires_at": <timestamp or null if permanent>,
  "confidence": <0.0-1.0 confidence in this classification>
}}
```

Classify this memory now."""


RANKING_PROMPT_TEMPLATE = """Rank the following memories by importance for future reference.

MEMORIES TO RANK:
{memories}

CURRENT PROJECT CONTEXT:
{project_context}

RANKING CRITERIA:
1. **Longevity**: Will this memory remain relevant over time?
2. **Actionability**: How useful is this memory for future decisions or actions?
3. **Uniqueness**: How unique is this information (avoid ranking common knowledge highly)
4. **User Impact**: How much does this affect the user's work or preferences?
5. **Project Relevance**: How directly related is this to the current project?

OUTPUT FORMAT:
```json
{{
  "ranked_memories": [
    {{
      "id": "<memory_id>",
      "rank": <1-10>,
      "score": <0.0-1.0>,
      "reasoning": "Brief explanation of why this rank was assigned"
    }}
  ],
  "top_memories": ["<memory_id>", "<memory_id>"],
  "rejected_memories": ["<memory_id>"]
}}
```

Rank these memories now, with 1 being the most important."""


class ExtractionPrompts:
    """Provides prompts for memory extraction, analysis, and classification."""

    @staticmethod
    def get_extraction_prompt(
        existing_memories: str = "",
        message_count: int = 0,
    ) -> str:
        """
        Get the prompt for extracting memories from a conversation.
        
        Args:
            existing_memories: Existing memory manifest for context
            message_count: Number of new messages since last extraction
            
        Returns:
            Formatted extraction prompt string
        """
        if not existing_memories:
            existing_memories = "No existing memories. This appears to be a new project."

        return EXTRACTION_PROMPT_TEMPLATE.format(
            existing_memories=existing_memories,
            message_count=message_count,
        )

    @staticmethod
    def get_analysis_prompt(
        memories: List[dict],
        related_memories: Optional[List[dict]] = None,
    ) -> str:
        """
        Get the prompt for analyzing extracted memories.
        
        Args:
            memories: List of extracted memory dictionaries
            related_memories: Optional list of related existing memories
            
        Returns:
            Formatted analysis prompt string
        """
        if not related_memories:
            related_memories = []

        memories_json = "\n".join(
            f"- [{m.get('id', 'unknown')}] {m.get('content', '')} (type: {m.get('type', 'unknown')})"
            for m in memories
        )
        related_json = "\n".join(
            f"- [{m.get('id', 'unknown')}] {m.get('content', '')}"
            for m in related_memories
        ) if related_memories else "No related existing memories."

        return ANALYSIS_PROMPT_TEMPLATE.format(
            memories=memories_json,
            related_memories=related_json,
        )

    @staticmethod
    def get_classification_prompt(
        content: str,
        memory_type: str,
        importance: float = 0.5,
    ) -> str:
        """
        Get the prompt for classifying a memory.
        
        Args:
            content: The memory content to classify
            memory_type: The initial memory type suggestion
            importance: The initial importance rating
            
        Returns:
            Formatted classification prompt string
        """
        return CLASSIFICATION_PROMPT_TEMPLATE.format(
            content=content,
            memory_type=memory_type,
            importance=importance,
        )

    @staticmethod
    def get_ranking_prompt(
        memories: List[dict],
        project_context: Optional[str] = None,
    ) -> str:
        """
        Get the prompt for ranking memories by importance.
        
        Args:
            memories: List of memories to rank
            project_context: Optional project context information
            
        Returns:
            Formatted ranking prompt string
        """
        if not project_context:
            project_context = "No specific project context provided."

        memories_json = "\n".join(
            f"- [{m.get('id', f'memory_{i}')}] {m.get('content', '')} (type: {m.get('type', 'unknown')}, importance: {m.get('importance', 0.5)})"
            for i, m in enumerate(memories)
        )

        return RANKING_PROMPT_TEMPLATE.format(
            memories=memories_json,
            project_context=project_context,
        )

    @staticmethod
    def get_memory_type_patterns() -> dict:
        """Get the patterns used for initial memory type classification."""
        return MEMORY_TYPE_PATTERNS.copy()

    @staticmethod
    def build_combined_prompt(
        message_count: int,
        existing_memories: str,
        skip_index: Optional[int] = None,
    ) -> str:
        """
        Build a combined extraction prompt with optional skip index.
        
        Args:
            message_count: Number of new messages
            existing_memories: Existing memory manifest
            skip_index: Optional index to skip extraction for certain turns
            
        Returns:
            Combined extraction prompt string
        """
        base_prompt = ExtractionPrompts.get_extraction_prompt(
            existing_memories=existing_memories,
            message_count=message_count,
        )

        if skip_index is not None and skip_index > 0:
            base_prompt += f"\n\nNOTE: Extraction turn {skip_index} - consider if this is worth extracting."

        return base_prompt

    @staticmethod
    def get_auto_only_prompt(
        message_count: int,
        existing_memories: str,
    ) -> str:
        """
        Build an auto-only extraction prompt (for non-team memory mode).
        
        Args:
            message_count: Number of new messages
            existing_memories: Existing memory manifest
            
        Returns:
            Auto-only extraction prompt string
        """
        return ExtractionPrompts.get_extraction_prompt(
            existing_memories=existing_memories,
            message_count=message_count,
        )
