"""
Type definitions for the Auto Dream memory consolidation system.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AutoDreamConfig:
    """Configuration for auto dream feature."""
    min_hours: float = 24.0
    min_sessions: int = 3


@dataclass
class DreamTurn:
    """A single turn in the dream consolidation process."""
    text: str
    tool_use_count: int = 0


@dataclass
class DreamTaskState:
    """State for a running dream consolidation task."""
    task_id: str
    status: str  # running, completed, failed, killed
    phase: str    # starting, updating
    sessions_reviewing: int
    files_touched: List[str] = field(default_factory=list)
    turns: List[DreamTurn] = field(default_factory=list)
    abort_controller: Optional[Any] = None
    prior_mtime: float = 0.0


@dataclass
class REPLHookContext:
    """Context passed to REPL hooks for dream execution."""
    messages: List[Dict[str, Any]]
    tool_use_context: Any  # ToolUseContext


@dataclass
class CacheSafeParams:
    """Parameters for cache-safe model queries."""
    system_prompt: str
    tools: List[Dict[str, Any]]
    model: str
    thinking_config: Dict[str, Any] = field(default_factory=dict)
    messages_prefix: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ForkAgentResult:
    """Result from running a forked agent."""
    success: bool
    messages: List[Dict[str, Any]] = field(default_factory=list)
    output: str = ""
    error: Optional[str] = None


@dataclass
class ToolPermission:
    """Permission decision for a tool call."""
    behavior: str  # "allow" or "deny"
    updated_input: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    decision_reason: Optional[Dict[str, Any]] = None


@dataclass
class DreamConsolidationResult:
    """Result of a dream consolidation operation."""
    task_id: str
    success: bool
    sessions_reviewed: int
    memories_created: int
    error: Optional[str] = None
