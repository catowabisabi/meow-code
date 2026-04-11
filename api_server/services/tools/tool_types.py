"""Type definitions for the tool orchestration service."""
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional


@dataclass
class ToolRequest:
    """Request to execute a tool."""
    id: str
    name: str
    input: dict[str, Any] = field(default_factory=dict)
    timeout_ms: Optional[int] = None


@dataclass
class ToolResponse:
    """Response from tool execution."""
    tool_use_id: str
    content: str
    is_error: bool = False
    error_message: Optional[str] = None


@dataclass
class ToolHook:
    """A hook for tool execution lifecycle."""
    name: str
    hook_type: str  # 'pre' or 'post'
    callback: Callable[..., Coroutine[Any, Any, Any]]
    priority: int = 0


@dataclass
class ExecutionContext:
    """Context for tool execution."""
    messages: list[Any] = field(default_factory=list)
    tools: list[Any] = field(default_factory=list)
    abort_controller: Optional[Any] = None
    tool_use_id: Optional[str] = None
    in_progress_tool_use_ids: set[str] = field(default_factory=set)
    
    def set_in_progress_tool_use_ids(self, updater: Callable[[set[str]], set[str]]) -> None:
        """Update the set of in-progress tool use IDs."""
        self.in_progress_tool_use_ids = updater(self.in_progress_tool_use_ids)
    
    def get_app_state(self) -> Any:
        """Get the application state."""
        return None


@dataclass
class MessageUpdate:
    """Update message from tool execution."""
    message: Optional[Any] = None
    new_context: Optional[ExecutionContext] = None


@dataclass
class ToolProgress:
    """Progress update from a tool."""
    tool_use_id: str
    data: Any


@dataclass
class PermissionDecision:
    """Decision from permission check."""
    behavior: str  # 'allow', 'deny', 'ask'
    message: Optional[str] = None
    updated_input: Optional[dict[str, Any]] = None
    decision_reason: Optional[Any] = None


@dataclass
class HookResult:
    """Result from a hook execution."""
    message: Optional[Any] = None
    blocking_error: Optional[str] = None
    prevent_continuation: bool = False
    stop_reason: Optional[str] = None
    permission_behavior: Optional[str] = None
    updated_input: Optional[dict[str, Any]] = None
    additional_contexts: list[Any] = field(default_factory=list)


@dataclass 
class ContextModifier:
    """Modifier for execution context."""
    tool_use_id: str
    modify_context: Callable[[ExecutionContext], ExecutionContext]


# Type aliases for async generators
MessageUpdateLazy = dict[str, Any]
ToolUseBlock = dict[str, Any]
AssistantMessage = dict[str, Any]


# MCP server types
McpServerType = str  # 'stdio' | 'sse' | 'http' | 'ws' | 'sdk' | 'sse-ide' | 'ws-ide' | 'claudeai-proxy'
