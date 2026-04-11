from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SuggestionType(str, Enum):
    USER_INTENT = "user_intent"
    STATED_INTENT = "stated_intent"
    COMPLETION = "completion"
    SIMILAR = "similar"
    AUTOCOMPLETE = "autocomplete"
    FOLLOWUP = "followup"


@dataclass
class Suggestion:
    prompt: str
    score: float
    source: str
    suggestion_type: SuggestionType = SuggestionType.USER_INTENT
    prompt_id: Optional[str] = None
    generation_request_id: Optional[str] = None
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())


@dataclass
class SuggestionContext:
    messages: List[Dict[str, Any]]
    current_input: str
    user_history: List[Dict[str, Any]] = field(default_factory=list)
    assistant_turn_count: int = 0
    is_api_error: bool = False
    cache_suppress_reason: Optional[str] = None
    pending_permission: bool = False
    elicitation_active: bool = False
    plan_mode: bool = False
    rate_limited: bool = False
    suggestion_enabled: bool = True


@dataclass
class SpeculationResult:
    messages: List[Dict[str, Any]]
    boundary: Optional[Dict[str, Any]] = None
    time_saved_ms: int = 0
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class SpeculationState:
    id: str
    status: str
    start_time: float
    suggestion_length: int
    tool_use_count: int = 0
    boundary: Optional[Dict[str, Any]] = None
    messages_ref: List[Dict[str, Any]] = field(default_factory=list)
    written_paths_ref: List[str] = field(default_factory=list)
    pipelined_suggestion: Optional[Suggestion] = None
    is_pipelined: bool = False


@dataclass
class SuggestionFilter:
    reason: str
    passed: bool = False


class SuggestionSuppressReason:
    DISABLED = "disabled"
    PENDING_PERMISSION = "pending_permission"
    ELICITATION_ACTIVE = "elicitation_active"
    PLAN_MODE = "plan_mode"
    RATE_LIMIT = "rate_limit"
    EARLY_CONVERSATION = "early_conversation"
    LAST_RESPONSE_ERROR = "last_response_error"
    CACHE_COLD = "cache_cold"
    ABORTED = "aborted"
    EMPTY = "empty"
    META_TEXT = "meta_text"
    META_WRAPPED = "meta_wrapped"
    ERROR_MESSAGE = "error_message"
    PREFIXED_LABEL = "prefixed_label"
    TOO_FEW_WORDS = "too_few_words"
    TOO_MANY_WORDS = "too_many_words"
    TOO_LONG = "too_long"
    MULTIPLE_SENTENCES = "multiple_sentences"
    HAS_FORMATTING = "has_formatting"
    EVALUATIVE = "evaluative"
    CLAUDE_VOICE = "claude_voice"