"""Type definitions for the tool execution system."""
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, Awaitable


@dataclass
class ToolDef:
    """
    Tool definition with metadata and executable handler.
    
    Attributes:
        name: Unique identifier for the tool
        description: Human-readable description of what the tool does
        input_schema: JSON schema for tool arguments (OpenAI function-calling format)
        is_read_only: Whether this tool only reads data (True enables parallel execution)
        risk_level: "low", "medium", or "high" - high risk tools require permission
        execute: Async callable that receives (arguments: dict, context: ToolContext) -> ToolResult
    """
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    is_read_only: bool = False
    risk_level: str = "low"  # "low", "medium", "high"
    execute: Callable[[Dict[str, Any], "ToolContext"], Awaitable["ToolResult"]] = field(default=None)

    def __post_init__(self):
        if self.execute is None:
            async def noop(args: Dict[str, Any], ctx: "ToolContext") -> "ToolResult":
                return ToolResult(tool_call_id="", output="Tool not implemented", is_error=True)
            self.execute = noop

    def model_dump(self, **kwargs) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "isReadOnly": self.is_read_only,
            "riskLevel": self.risk_level,
        }


@dataclass
class ToolResult:
    """Result from executing a tool."""
    tool_call_id: str
    output: str
    is_error: bool = False

    def model_dump(self, **kwargs) -> dict:
        return {
            "tool_call_id": self.tool_call_id,
            "output": self.output,
            "isError": self.is_error,
        }


@dataclass
class ToolCall:
    """A tool call request from the AI."""
    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self, **kwargs) -> dict:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}

    @classmethod
    def from_dict(cls, data: dict) -> "ToolCall":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            arguments=data.get("arguments", {}),
        )


@dataclass
class ToolContext:
    """
    Execution context passed to tool handlers.
    
    Attributes:
        cwd: Current working directory for the tool execution
        abort_signal: Optional signal to check for abortion
        request_permission: Async callable(tool_name, args, description) -> bool
        on_progress: Async callable for progress updates
    """
    cwd: str
    abort_signal: Optional[Callable[[], bool]] = None
    request_permission: Optional[Callable[[str, Dict[str, Any], str], Awaitable[bool]]] = None
    on_progress: Optional[Callable[["ToolProgress"], Awaitable[None]]] = None


@dataclass
class ToolProgress:
    """Progress update from a running tool."""
    tool_id: str = ""
    tool_name: str = ""
    message: str = ""
    progress: float = 0.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ToolCallResult:
    """Result of a tool call execution."""
    tool_call_id: str
    name: str
    output: str
    is_error: bool = False

    def model_dump(self, **kwargs) -> dict:
        return {
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "output": self.output,
            "isError": self.is_error,
        }


# Event types for tool execution monitoring
@dataclass
class ToolExecutionEvent:
    """Base class for tool execution events."""
    type: str


@dataclass
class ToolStartEvent(ToolExecutionEvent):
    """Event emitted when a tool starts execution."""
    tool_id: str = ""
    tool_name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.type = "tool_start"


@dataclass
class ToolProgressEvent(ToolExecutionEvent):
    """Event emitted when a tool reports progress."""
    tool_id: str = ""
    tool_name: str = ""
    progress: ToolProgress = field(default_factory=ToolProgress)

    def __post_init__(self):
        self.type = "tool_progress"


@dataclass
class ToolEndEvent(ToolExecutionEvent):
    """Event emitted when a tool completes execution."""
    tool_id: str = ""
    tool_name: str = ""
    result: Optional[ToolCallResult] = None

    def __post_init__(self):
        self.type = "tool_end"


@dataclass
class PermissionRequestEvent(ToolExecutionEvent):
    """Event emitted when requesting permission for a high-risk tool."""
    tool_id: str = ""
    tool_name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self):
        self.type = "permission_request"


# Union type for all events
ToolEvent = ToolStartEvent | ToolProgressEvent | ToolEndEvent | PermissionRequestEvent