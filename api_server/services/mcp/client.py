from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass

class TransportType(Enum):
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"
    HTTP = "http"

class MCPError(Exception):
    def __init__(self, code: str, message: str, data: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)

class MCPErrorCode:
    PARSE_ERROR = "parse_error"
    INVALID_REQUEST = "invalid_request"
    METHOD_NOT_FOUND = "method_not_found"
    INVALID_PARAMS = "invalid_params"
    INTERNAL_ERROR = "internal_error"
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_EXECUTION_ERROR = "tool_execution_error"
    CONNECTION_ERROR = "connection_error"

@dataclass
class WSConnectionConfig:
    url: str
    headers: Optional[Dict[str, str]] = None
    ping_interval: int = 30
    ping_timeout: int = 10

@dataclass
class ToolResult:
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None

class MCPClient:
    def __init__(
        self,
        transport_type: TransportType = TransportType.STDIO,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
    ):
        self.transport_type = transport_type
        self.command = command
        self.args = args or []
        self.url = url
        self._connected = False
        self._handlers: Dict[str, Callable] = {}
        self._ws_config: Optional[WSConnectionConfig] = None

    def _map_transport_type(self, transport: str) -> TransportType:
        transport_map = {
            "stdio": TransportType.STDIO,
            "sse": TransportType.SSE,
            "websocket": TransportType.WEBSOCKET,
            "ws": TransportType.WEBSOCKET,
            "http": TransportType.HTTP,
            "https": TransportType.HTTP,
        }
        return transport_map.get(transport.lower(), TransportType.STDIO)

    def connect(self) -> bool:
        if self.transport_type == TransportType.STDIO:
            return self._connect_stdio()
        elif self.transport_type == TransportType.SSE:
            return self._connect_sse()
        elif self.transport_type == TransportType.WEBSOCKET:
            return self._connect_websocket()
        elif self.transport_type == TransportType.HTTP:
            return self._connect_http()
        return False

    def _connect_stdio(self) -> bool:
        if not self.command:
            raise MCPError(MCPErrorCode.CONNECTION_ERROR, "Command not specified for stdio transport")
        self._connected = True
        return True

    def _connect_sse(self) -> bool:
        if not self.url:
            raise MCPError(MCPErrorCode.CONNECTION_ERROR, "URL not specified for SSE transport")
        self._connected = True
        return True

    def _connect_websocket(self) -> bool:
        if not self.url:
            raise MCPError(MCPErrorCode.CONNECTION_ERROR, "URL not specified for WebSocket transport")
        self._ws_config = WSConnectionConfig(url=self.url)
        self._connected = True
        return True

    def _connect_http(self) -> bool:
        if not self.url:
            raise MCPError(MCPErrorCode.CONNECTION_ERROR, "URL not specified for HTTP transport")
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False
        self._handlers.clear()

    def send_message(self, method: str, params: Optional[dict] = None) -> Dict[str, Any]:
        if not self._connected:
            raise MCPError(MCPErrorCode.CONNECTION_ERROR, "Not connected to MCP server")
        
        if not method:
            raise MCPError(MCPErrorCode.INVALID_REQUEST, "Method name is required")
        
        try:
            return {
                "jsonrpc": "2.0",
                "id": "1",
                "result": {"content": []}
            }
        except Exception as e:
            raise MCPError(MCPErrorCode.INTERNAL_ERROR, f"Failed to send message: {str(e)}")

    def on_notification(self, method: str, handler: Callable) -> None:
        if not method:
            raise MCPError(MCPErrorCode.INVALID_REQUEST, "Method name is required for notification handler")
        self._handlers[method] = handler

    def is_connected(self) -> bool:
        return self._connected

    def get_ws_url(self) -> Optional[str]:
        if self._ws_config:
            return self._ws_config.url
        if self.transport_type == TransportType.WEBSOCKET and self.url:
            return self.url
        return None

class MCPService:
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self._tools: Dict[str, Callable] = {}

    def create_client(
        self,
        client_id: str,
        transport_type: str = "stdio",
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
    ) -> MCPClient:
        transport = TransportType.STDIO
        if transport_type == "sse":
            transport = TransportType.SSE
        elif transport_type in ("websocket", "ws"):
            transport = TransportType.WEBSOCKET
        elif transport_type in ("http", "https"):
            transport = TransportType.HTTP
        
        client = MCPClient(
            transport_type=transport,
            command=command,
            args=args,
            url=url,
        )
        self.clients[client_id] = client
        return client

    def get_client(self, client_id: str) -> Optional[MCPClient]:
        return self.clients.get(client_id)

    def remove_client(self, client_id: str) -> bool:
        if client_id in self.clients:
            client = self.clients[client_id]
            client.disconnect()
            del self.clients[client_id]
            return True
        return False

    def register_tool(self, name: str, handler: Callable) -> None:
        if not name:
            raise MCPError(MCPErrorCode.INVALID_REQUEST, "Tool name is required")
        self._tools[name] = handler

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def execute_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
        start_time = time.time()
        
        if name not in self._tools:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found",
            )
        
        try:
            tool = self._tools[name]
            args = arguments or {}
            result = tool(**args)
            execution_time = (time.time() - start_time) * 1000
            return ToolResult(
                success=True,
                result=result,
                execution_time_ms=execution_time,
            )
        except TypeError as e:
            return ToolResult(
                success=False,
                error=f"Invalid arguments for tool '{name}': {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )