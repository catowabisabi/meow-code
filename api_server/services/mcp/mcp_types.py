"""
Type definitions for MCP (Model Context Protocol) service.

This module provides Python type definitions that mirror the TypeScript types
defined in the MCP SDK and the Claude Code implementation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)


class ConfigScope(str, Enum):
    """Configuration scope for MCP servers."""
    LOCAL = "local"
    USER = "user"
    PROJECT = "project"
    DYNAMIC = "dynamic"
    ENTERPRISE = "enterprise"
    CLAUDEAI = "claudeai"
    MANAGED = "managed"


class Transport(str, Enum):
    """Transport type for MCP server connections."""
    STDIO = "stdio"
    SSE = "sse"
    SSE_IDE = "sse-ide"
    HTTP = "http"
    WS = "ws"
    SDK = "sdk"


# Configuration Schemas

@dataclass
class McpStdioServerConfig:
    """Configuration for stdio-based MCP server."""
    type: Literal["stdio"] = "stdio"
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None


@dataclass
class McpOAuthConfig:
    """OAuth configuration for MCP server."""
    client_id: Optional[str] = None
    callback_port: Optional[int] = None
    auth_server_metadata_url: Optional[str] = None
    xaa: bool = False


@dataclass
class McpSSEServerConfig:
    """Configuration for SSE-based MCP server."""
    type: Literal["sse"] = "sse"
    url: str = ""
    headers: Optional[Dict[str, str]] = None
    headers_helper: Optional[str] = None
    oauth: Optional[McpOAuthConfig] = None


@dataclass
class McpSSEIDEServerConfig:
    """Configuration for IDE SSE MCP server (internal only)."""
    type: Literal["sse-ide"] = "sse-ide"
    url: str = ""
    ide_name: str = ""
    ide_running_in_windows: Optional[bool] = None


@dataclass
class McpWebSocketIDEServerConfig:
    """Configuration for IDE WebSocket MCP server (internal only)."""
    type: Literal["ws-ide"] = "ws-ide"
    url: str = ""
    ide_name: str = ""
    auth_token: Optional[str] = None
    ide_running_in_windows: Optional[bool] = None


@dataclass
class McpHTTPServerConfig:
    """Configuration for HTTP-based MCP server."""
    type: Literal["http"] = "http"
    url: str = ""
    headers: Optional[Dict[str, str]] = None
    headers_helper: Optional[str] = None
    oauth: Optional[McpOAuthConfig] = None


@dataclass
class McpWebSocketServerConfig:
    """Configuration for WebSocket-based MCP server."""
    type: Literal["ws"] = "ws"
    url: str = ""
    headers: Optional[Dict[str, str]] = None
    headers_helper: Optional[str] = None


@dataclass
class McpSdkServerConfig:
    """Configuration for SDK-based MCP server."""
    type: Literal["sdk"] = "sdk"
    name: str = ""


@dataclass
class McpClaudeAIProxyServerConfig:
    """Configuration for Claude.ai proxy MCP server."""
    type: Literal["claudeai-proxy"] = "claudeai-proxy"
    url: str = ""
    id: str = ""


McpServerConfig = Union[
    McpStdioServerConfig,
    McpSSEServerConfig,
    McpSSEIDEServerConfig,
    McpWebSocketIDEServerConfig,
    McpHTTPServerConfig,
    McpWebSocketServerConfig,
    McpSdkServerConfig,
    McpClaudeAIProxyServerConfig,
]


@dataclass
class ScopedMcpServerConfig:
    """MCP server configuration with scope information."""
    scope: Optional[ConfigScope] = None
    plugin_source: Optional[str] = None
    type: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    headers_helper: Optional[str] = None
    oauth: Optional[McpOAuthConfig] = None
    ide_name: Optional[str] = None
    ide_running_in_windows: Optional[bool] = None
    auth_token: Optional[str] = None
    name: Optional[str] = None
    id: Optional[str] = None


@dataclass
class McpJsonConfig:
    """Root MCP configuration format."""
    mcpServers: Dict[str, McpServerConfig] = field(default_factory=dict)


# Server Connection Types

@dataclass
class ServerCapabilities:
    """MCP server capabilities."""
    tools: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    elicitation: Optional[Dict[str, Any]] = None


@dataclass
class ConnectedMCPServer:
    """Successfully connected MCP server."""
    client: Any
    name: str
    type: Literal["connected"] = "connected"
    capabilities: Optional[ServerCapabilities] = None
    server_info: Optional[Dict[str, str]] = None
    instructions: Optional[str] = None
    config: Optional[ScopedMcpServerConfig] = None
    cleanup: Optional[Callable[[], Any]] = None


@dataclass
class FailedMCPServer:
    """Failed MCP server connection."""
    name: str
    type: Literal["failed"] = "failed"
    config: Optional[ScopedMcpServerConfig] = None
    error: Optional[str] = None


@dataclass
class NeedsAuthMCPServer:
    """MCP server requiring authentication."""
    name: str
    type: Literal["needs-auth"] = "needs-auth"
    config: Optional[ScopedMcpServerConfig] = None


@dataclass
class PendingMCPServer:
    """Pending MCP server connection."""
    name: str
    type: Literal["pending"] = "pending"
    config: Optional[ScopedMcpServerConfig] = None
    reconnect_attempt: Optional[int] = None
    max_reconnect_attempts: Optional[int] = None


@dataclass
class DisabledMCPServer:
    """Disabled MCP server."""
    name: str
    type: Literal["disabled"] = "disabled"
    config: Optional[ScopedMcpServerConfig] = None


MCPServerConnection = Union[
    ConnectedMCPServer,
    FailedMCPServer,
    NeedsAuthMCPServer,
    PendingMCPServer,
    DisabledMCPServer,
]


# Resource Types

@dataclass
class ServerResource:
    """MCP resource with server name."""
    uri: str
    name: Optional[str] = None
    description: Optional[str] = None
    mime_type: Optional[str] = None
    server: Optional[str] = None


# Serialization Types

@dataclass
class SerializedTool:
    """Serialized MCP tool."""
    name: str
    description: str
    input_json_schema: Optional[Dict[str, Any]] = None
    is_mcp: bool = False
    original_tool_name: Optional[str] = None


@dataclass
class SerializedClient:
    """Serialized MCP client state."""
    name: str
    type: Literal["connected", "failed", "needs-auth", "pending", "disabled"]
    capabilities: Optional[ServerCapabilities] = None


@dataclass
class MCPCliState:
    """CLI state for MCP servers."""
    clients: List[SerializedClient] = field(default_factory=list)
    configs: Dict[str, ScopedMcpServerConfig] = field(default_factory=dict)
    tools: List[SerializedTool] = field(default_factory=list)
    resources: Dict[str, List[ServerResource]] = field(default_factory=dict)
    normalized_names: Optional[Dict[str, str]] = None


# Transport Protocol

@runtime_checkable
class TransportProtocol(Protocol):
    """Protocol for MCP transport implementations."""

    def start(self) -> Any: ...
    def send(self, message: Dict[str, Any]) -> Any: ...
    def close(self) -> Any: ...
    onclose: Optional[Callable[[], None]] = None
    onerror: Optional[Callable[[Exception], None]] = None
    onmessage: Optional[Callable[[Dict[str, Any]], None]] = None


# JSON-RPC Types

JSONRPCMessage = Dict[str, Any]
JSONRPCRequest = Dict[str, Any]
JSONRPCResponse = Dict[str, Any]


# Tool Types

@dataclass
class Tool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    is_mcp: bool = False
    original_tool_name: Optional[str] = None


@dataclass
class CallToolResult:
    """Result from calling an MCP tool."""
    content: List[Dict[str, Any]]
    is_error: bool = False
    _meta: Optional[Dict[str, Any]] = None


# Error Types

class McpError(Exception):
    """Base MCP error."""
    def __init__(self, message: str, code: int = -32000):
        super().__init__(message)
        self.code = code
        self.message = message


class McpAuthError(McpError):
    """MCP authentication error."""
    def __init__(self, message: str, server_name: str):
        super().__init__(message, code=-32001)
        self.server_name = server_name


class ConnectionClosedError(McpError):
    """MCP connection closed error."""
    def __init__(self, message: str = "Connection closed"):
        super().__init__(message, code=-32000)


class RequestTimeoutError(McpError):
    """MCP request timeout error."""
    def __init__(self, message: str = "Request timeout"):
        super().__init__(message, code=-32001)
