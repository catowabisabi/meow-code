from typing import Literal, Optional, List, Union, TypedDict


# ─── Client → Server Messages ─────────────────────────────────


class ClientUserMessage(TypedDict):
    type: Literal["user_message"]
    content: str
    sessionId: Optional[str]
    mode: Optional[str]
    model: Optional[str]
    provider: Optional[str]
    attachments: Optional[List[dict]]


class ClientPermissionResponse(TypedDict):
    type: Literal["permission_response"]
    toolUseId: str
    allowed: bool


class ClientAbort(TypedDict):
    type: Literal["abort"]


class ClientPing(TypedDict):
    type: Literal["ping"]


class ClientSwitchModel(TypedDict):
    type: Literal["switch_model"]
    model: str
    provider: str


ClientMessage = Union[
    ClientUserMessage,
    ClientPermissionResponse,
    ClientAbort,
    ClientSwitchModel,
    ClientPing,
]


# ─── Server → Client Messages ─────────────────────────────────


class ServerStreamStart(TypedDict):
    type: Literal["stream_start"]
    messageId: str
    sessionId: str
    model: str
    provider: str


class ServerStreamDelta(TypedDict):
    type: Literal["stream_delta"]
    contentType: Literal["text", "thinking"]
    text: str


class ServerToolUseStart(TypedDict):
    type: Literal["tool_use_start"]
    toolId: str
    toolName: str
    input: dict


class ServerToolResult(TypedDict):
    type: Literal["tool_result"]
    toolId: str
    toolName: str
    output: str
    isError: bool


class ServerPermissionRequest(TypedDict):
    type: Literal["permission_request"]
    toolName: str
    toolId: str
    input: dict
    description: str


class ServerStreamEnd(TypedDict):
    type: Literal["stream_end"]
    usage: Optional[dict]
    stopReason: Optional[str]


class ServerError(TypedDict):
    type: Literal["error"]
    message: str
    code: Optional[str]


class ServerSessionInfo(TypedDict):
    type: Literal["session_info"]
    sessionId: str
    model: str
    provider: str


class ServerModelSwitched(TypedDict):
    type: Literal["model_switched"]
    model: str
    provider: str


class ServerPong(TypedDict):
    type: Literal["pong"]


class ServerTitleUpdated(TypedDict):
    type: Literal["title_updated"]
    sessionId: str
    title: str


ServerMessage = Union[
    ServerStreamStart,
    ServerStreamDelta,
    ServerToolUseStart,
    ServerToolResult,
    ServerPermissionRequest,
    ServerStreamEnd,
    ServerError,
    ServerSessionInfo,
    ServerModelSwitched,
    ServerPong,
    ServerTitleUpdated,
]


# ─── Content Block Types (internal) ───────────────────────────


class TextContentBlock(TypedDict):
    type: Literal["text"]
    text: str


class ThinkingContentBlock(TypedDict):
    type: Literal["thinking"]
    text: str


class ToolUseContentBlock(TypedDict):
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict


class ToolResultContentBlock(TypedDict):
    type: Literal["tool_result"]
    tool_use_id: str
    content: str
    is_error: bool


class ImageContentBlock(TypedDict):
    type: Literal["image"]
    source: dict


ContentBlock = Union[
    TextContentBlock,
    ThinkingContentBlock,
    ToolUseContentBlock,
    ToolResultContentBlock,
    ImageContentBlock,
]


# ─── Internal Types ────────────────────────────────────────────


class UnifiedMessage(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: List[ContentBlock]


class UnifiedToolDef(TypedDict):
    name: str
    description: str
    inputSchema: dict


class ToolCall(TypedDict):
    id: str
    name: str
    arguments: dict


class ToolCallResult(TypedDict):
    tool_call_id: str
    output: str
    isError: bool


class ToolExecutorEvent(TypedDict):
    type: Literal["tool_start", "tool_progress", "tool_end"]
    toolId: Optional[str]
    toolName: Optional[str]
    input: Optional[dict]
    result: Optional[ToolCallResult]
