from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional, Protocol, TypedDict


class CompactStrategy(Enum):
    TIME_BASED = "time_based"
    SESSION_MEMORY = "session_memory"
    MICRO = "micro"
    FULL = "full"
    PARTIAL = "partial"


class PartialCompactDirection(Enum):
    FROM = "from"
    UP_TO = "up_to"


@dataclass
class TimeBasedConfig:
    enabled: bool = False
    gap_threshold_minutes: int = 60
    keep_recent: int = 5


@dataclass
class SessionMemoryCompactConfig:
    min_tokens: int = 10_000
    min_text_block_messages: int = 5
    max_tokens: int = 40_000


DEFAULT_SM_COMPACT_CONFIG = SessionMemoryCompactConfig(
    min_tokens=10_000,
    min_text_block_messages=5,
    max_tokens=40_000,
)


@dataclass
class CompactConfig:
    max_output_tokens: int = 20_000
    prompt_cache_sharing_enabled: bool = True
    streaming_retry_enabled: bool = False
    max_streaming_retries: int = 2
    time_based: TimeBasedConfig = field(default_factory=TimeBasedConfig)
    session_memory: SessionMemoryCompactConfig = field(
        default_factory=SessionMemoryCompactConfig
    )


@dataclass
class MicroCompactInput:
    messages: List[Any]
    query_source: Optional[str] = None
    tool_use_context: Optional[Any] = None


@dataclass
class PostCompactCleanupResult:
    cleared_caches: List[str] = field(default_factory=list)
    cleared_state: List[str] = field(default_factory=list)


@dataclass
class CompactWarningState:
    suppressed: bool = False
    reason: Optional[str] = None


class CompactWarningHook(Protocol):
    def __call__(self, state: CompactWarningState) -> None:
        ...


@dataclass
class TokenStats:
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


@dataclass
class CompactionUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


class CompactMetadata(TypedDict, total=False):
    pre_compact_discovered_tools: Optional[List[str]]
    preserved_segment: Optional["PreservedSegment"]


@dataclass
class PreservedSegment:
    head_uuid: str
    anchor_uuid: str
    tail_uuid: str


@dataclass
class SummarizeMetadata:
    messages_summarized: int
    user_context: Optional[str] = None
    direction: PartialCompactDirection = PartialCompactDirection.FROM


@dataclass
class CompactionResult:
    boundary_marker: Any
    summary_messages: List[Any]
    attachments: List[Any] = field(default_factory=list)
    hook_results: List[Any] = field(default_factory=list)
    messages_to_keep: Optional[List[Any]] = None
    user_display_message: Optional[str] = None
    pre_compact_token_count: Optional[int] = None
    post_compact_token_count: Optional[int] = None
    true_post_compact_token_count: Optional[int] = None
    compaction_usage: Optional[CompactionUsage] = None


@dataclass
class RecompactionInfo:
    is_recompaction_in_chain: bool = False
    turns_since_previous_compact: int = -1
    previous_compact_turn_id: Optional[str] = None
    auto_compact_threshold: int = 0
    query_source: Optional[str] = None


@dataclass
class AutoCompactThreshold:
    effective_context_window: int
    auto_compact_threshold: int
    warning_threshold: int
    error_threshold: int
    blocking_limit: int


@dataclass
class TokenWarningState:
    percent_left: int
    is_above_warning_threshold: bool
    is_above_error_threshold: bool
    is_above_auto_compact_threshold: bool
    is_at_blocking_limit: bool


@dataclass
class AutoCompactTrackingState:
    compacted: bool = False
    turn_counter: int = 0
    turn_id: str = ""
    consecutive_failures: int = 0


@dataclass
class PendingCacheEdits:
    trigger: str = "auto"
    deleted_tool_ids: List[str] = field(default_factory=list)
    baseline_cache_deleted_tokens: int = 0


@dataclass
class MicroCompactResult:
    messages: List[Any]
    compaction_info: Optional[dict] = None


POST_COMPACT_MAX_FILES_TO_RESTORE = 5
POST_COMPACT_TOKEN_BUDGET = 50_000
POST_COMPACT_MAX_TOKENS_PER_FILE = 5_000
POST_COMPACT_MAX_TOKENS_PER_SKILL = 5_000
POST_COMPACT_SKILLS_TOKEN_BUDGET = 25_000
AUTOCOMPACT_BUFFER_TOKENS = 13_000
WARNING_THRESHOLD_BUFFER_TOKENS = 20_000
ERROR_THRESHOLD_BUFFER_TOKENS = 20_000
MANUAL_COMPACT_BUFFER_TOKENS = 3_000
MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3

ERROR_MESSAGE_NOT_ENOUGH_MESSAGES = "Not enough messages to compact."
ERROR_MESSAGE_PROMPT_TOO_LONG = (
    "Conversation too long. Press esc twice to go up a few messages and try again."
)
ERROR_MESSAGE_USER_ABORT = "API Error: Request was aborted."
ERROR_MESSAGE_INCOMPLETE_RESPONSE = (
    "Compaction interrupted · This may be due to network issues — please try again."
)