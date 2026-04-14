"""Enhanced type definitions for the tool execution system - bridging gap with TypeScript Tool.ts"""
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, Awaitable, List, Union
from enum import Enum


class PermissionBehavior(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    error_message: Optional[str] = None
    error_code: Optional[int] = None


@dataclass
class PermissionResult:
    """Result of permission check."""
    behavior: PermissionBehavior = PermissionBehavior.ALLOW
    updated_input: Optional[Dict[str, Any]] = None


@dataclass
class ToolDef:
    """
    Enhanced tool definition with metadata and executable handler.
    
    Bridges gap with TypeScript Tool interface (src/Tool.ts).
    
    Additional fields beyond basic tool:
        - aliases: Optional alternative names
        - searchHint: One-line capability phrase for ToolSearch
        - validateInput: Input validation function
        - checkPermissions: Permission check function
        - isEnabled: Whether tool is currently enabled
        - isConcurrencySafe: Whether tool can run concurrently
        - isDestructive: Whether tool performs irreversible operations
        - isMcp: Whether this is an MCP tool
        - isLsp: Whether this is an LSP tool
        - shouldDefer: Whether tool requires ToolSearch before calling
        - alwaysLoad: Whether to always include in initial prompt
        - maxResultSizeChars: Max result size before persisting to disk
        - interruptBehavior: What happens when user submits new message
        - getPath: Get file path from input
        - userFacingName: Custom display name
        - getActivityDescription: Short activity description for spinners
        - toAutoClassifierInput: Input for auto-mode security classifier
        - prompt: Custom prompt generation
    """
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    is_read_only: bool = False
    risk_level: str = "low"
    execute: Callable[[Dict[str, Any], "ToolContext"], Awaitable["ToolResult"]] = field(default=None)
    
    aliases: Optional[List[str]] = None
    search_hint: Optional[str] = None
    
    validate_input: Optional[Callable[[Dict[str, Any], "ToolContext"], Awaitable[ValidationResult]]] = None
    check_permissions: Optional[Callable[[Dict[str, Any], "ToolContext"], Awaitable[PermissionResult]]] = None
    is_enabled: Optional[Callable[[], bool]] = None
    is_concurrency_safe: Optional[Callable[[Dict[str, Any]], bool]] = None
    is_destructive: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    is_mcp: bool = False
    is_lsp: bool = False
    should_defer: bool = False
    always_load: bool = False
    max_result_size_chars: int = 100000
    strict: bool = False
    
    interrupt_behavior: str = "block"
    
    get_path: Optional[Callable[[Dict[str, Any]], str]] = None
    user_facing_name: Optional[Callable[[Optional[Dict[str, Any]]], str]] = None
    get_activity_description: Optional[Callable[[Optional[Dict[str, Any]]], Optional[str]]] = None
    to_auto_classifier_input: Optional[Callable[[Dict[str, Any]], Any]] = None
    
    mcp_server_name: Optional[str] = None
    mcp_tool_name: Optional[str] = None

    def __post_init__(self):
        if self.execute is None:
            async def noop(args: Dict[str, Any], ctx: "ToolContext") -> "ToolResult":
                return ToolResult(tool_call_id="", output="Tool not implemented", is_error=True)
            self.execute = noop
        
        if self.aliases is None:
            self.aliases = []
        if self.search_hint is None:
            self.search_hint = ""

    def model_dump(self, **kwargs) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "isReadOnly": self.is_read_only,
            "riskLevel": self.risk_level,
            "aliases": self.aliases,
            "searchHint": self.search_hint,
            "isMcp": self.is_mcp,
            "isLsp": self.is_lsp,
            "shouldDefer": self.should_defer,
            "alwaysLoad": self.always_load,
            "maxResultSizeChars": self.max_result_size_chars,
        }

    def matches_name(self, name: str) -> bool:
        if self.name == name:
            return True
        if self.aliases and name in self.aliases:
            return True
        return False

    async def validate(self, input_args: Dict[str, Any], context: "ToolContext") -> ValidationResult:
        if self.validate_input:
            return await self.validate_input(input_args, context)
        return ValidationResult(is_valid=True)

    async def check_perm(self, input_args: Dict[str, Any], context: "ToolContext") -> PermissionResult:
        if self.check_permissions:
            return await self.check_permissions(input_args, context)
        return PermissionResult(behavior=PermissionBehavior.ALLOW, updated_input=input_args)

    def enabled(self) -> bool:
        if self.is_enabled:
            return self.is_enabled()
        return True

    def concurrency_safe(self, input_args: Dict[str, Any]) -> bool:
        if self.is_concurrency_safe:
            return self.is_concurrency_safe(input_args)
        return False

    def destructive(self, input_args: Dict[str, Any]) -> bool:
        if self.is_destructive:
            return self.is_destructive(input_args)
        return False


@dataclass
class ToolResult:
    """Result from executing a tool."""
    tool_call_id: str
    output: str
    is_error: bool = False
    new_messages: Optional[List[Dict[str, Any]]] = None

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
    
    Enhanced from TypeScript ToolUseContext interface.
    """
    cwd: str
    abort_signal: Optional[Callable[[], bool]] = None
    request_permission: Optional[Callable[[str, Dict[str, Any], str], Awaitable[bool]]] = None
    on_progress: Optional[Callable[["ToolProgress"], Awaitable[None]]] = None
    
    messages: Optional[List[Dict[str, Any]]] = None
    tools: Optional[List["ToolDef"]] = None
    
    is_non_interactive: bool = False
    verbose: bool = False
    debug: bool = False


@dataclass
class ToolProgress:
    """Progress update from a running tool."""
    tool_id: str = ""
    tool_name: str = ""
    message: str = ""
    progress: float = 0.0
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


@dataclass
class ToolExecutionEvent:
    """Base class for tool execution events."""
    type: str


@dataclass
class ToolStartEvent(ToolExecutionEvent):
    tool_id: str = ""
    tool_name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.type = "tool_start"


@dataclass
class ToolProgressEvent(ToolExecutionEvent):
    tool_id: str = ""
    tool_name: str = ""
    progress: ToolProgress = field(default_factory=ToolProgress)

    def __post_init__(self):
        self.type = "tool_progress"


@dataclass
class ToolEndEvent(ToolExecutionEvent):
    tool_id: str = ""
    tool_name: str = ""
    result: Optional[ToolCallResult] = None

    def __post_init__(self):
        self.type = "tool_end"


@dataclass
class PermissionRequestEvent(ToolExecutionEvent):
    tool_id: str = ""
    tool_name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self):
        self.type = "permission_request"


ToolEvent = ToolStartEvent | ToolProgressEvent | ToolEndEvent | PermissionRequestEvent


Tool = ToolDef
Tools = List[ToolDef]
