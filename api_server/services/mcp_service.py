"""
MCP Service - Model Context Protocol client implementation.

Provides MCP server discovery, connection, tool calling, and resource management.
Based on the MCP JSON-RPC 2.0 protocol specification.
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

try:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    from mcp.client.streamable_http import streamable_http_client
    from mcp.client.sse import sse_client
    from mcp.types import Tool as MCPTool, Resource as MCPResource

    MCP_SDK_AVAILABLE = True
except ImportError as e:
    MCP_SDK_AVAILABLE = False
    logger.warning(f"MCP SDK not available: {e}. Install with: pip install mcp")


class McpTransport(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WS = "ws"


@dataclass
class McpServerConfig:
    """MCP server configuration."""
    name: str
    transport: McpTransport
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] | None = None
    auth_token: str | None = None


@dataclass
class McpConnection:
    """MCP server connection state."""
    name: str
    server_config: McpServerConfig
    status: str = "disconnected"
    tools: list[dict] = field(default_factory=list)
    resources: list[dict] = field(default_factory=list)
    capabilities: dict | None = None


@dataclass
class McpToolResult:
    """Result from an MCP tool call."""
    content: list[dict] = field(default_factory=list)
    is_error: bool = False
    error: str | None = None


class McpClient:
    """
    MCP client for connecting to MCP servers.
    
    Supports multiple transport types:
    - STDIO: Local subprocess communication
    - SSE: Server-Sent Events over HTTP
    - HTTP: Streamable HTTP transport
    - WS: WebSocket transport
    """
    
    def __init__(self, name: str, config: McpServerConfig):
        self.name = name
        self.config = config
        self.status = "disconnected"
        self.tools = []
        self.resources = []
        self.capabilities = None
        self._session: ClientSession | None = None
        self._read_stream: Any = None
        self._write_stream: Any = None
        self._cleanup: Any = None
        self._progress_callback: Callable | None = None

    def set_progress_callback(self, callback: Callable) -> None:
        """Set callback for progress updates during tool calls."""
        self._progress_callback = callback

    async def connect(self) -> bool:
        """
        Connect to the MCP server.
        
        Returns:
            True if connection successful, False otherwise.
        """
        if not MCP_SDK_AVAILABLE:
            logger.error(f"MCP SDK not available for server {self.name}")
            return False
        
        try:
            if self.config.transport == McpTransport.STDIO:
                return await self._connect_stdio()
            elif self.config.transport == McpTransport.SSE:
                return await self._connect_sse()
            elif self.config.transport == McpTransport.HTTP:
                return await self._connect_http()
            elif self.config.transport == McpTransport.WS:
                return await self._connect_ws()
            logger.error(f"Unsupported transport: {self.config.transport}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.name}: {e}")
            self.status = "failed"
            return False

    async def _connect_stdio(self) -> bool:
        """Connect via STDIO transport."""
        if not self.config.command:
            logger.error(f"No command specified for STDIO server {self.name}")
            return False
        
        try:
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env if self.config.env else None,
            )
            self._cleanup = stdio_client(server_params)
            self._read_stream, self._write_stream = await self._cleanup.__aenter__()
            self._session = ClientSession(self._read_stream, self._write_stream)
            await self._session.initialize()
            self.status = "connected"
            await self._load_server_info()
            await self._load_tools()
            return True
        except Exception as e:
            logger.error(f"STDIO connection failed for {self.name}: {e}")
            return False

    async def _connect_sse(self) -> bool:
        """Connect via SSE transport."""
        if not self.config.url:
            logger.error(f"No URL specified for SSE server {self.name}")
            return False
        
        try:
            headers = dict(self.config.headers or {})
            if self.config.auth_token:
                headers["Authorization"] = f"Bearer {self.config.auth_token}"
            
            self._cleanup = sse_client(
                self.config.url,
                headers=headers,
            )
            self._read_stream, self._write_stream = await self._cleanup.__aenter__()
            self._session = ClientSession(self._read_stream, self._write_stream)
            await self._session.initialize()
            self.status = "connected"
            await self._load_server_info()
            await self._load_tools()
            return True
        except Exception as e:
            logger.error(f"SSE connection failed for {self.name}: {e}")
            return False

    async def _connect_http(self) -> bool:
        """Connect via HTTP transport."""
        if not self.config.url:
            logger.error(f"No URL specified for HTTP server {self.name}")
            return False
        
        try:
            headers = dict(self.config.headers or {})
            if self.config.auth_token:
                headers["Authorization"] = f"Bearer {self.config.auth_token}"
            
            self._cleanup = streamable_http_client(
                self.config.url,
                headers=headers,
            )
            self._read_stream, self._write_stream = await self._cleanup.__aenter__()
            self._session = ClientSession(self._read_stream, self._write_stream)
            await self._session.initialize()
            self.status = "connected"
            await self._load_server_info()
            await self._load_tools()
            return True
        except Exception as e:
            logger.error(f"HTTP connection failed for {self.name}: {e}")
            return False

    async def _connect_ws(self) -> bool:
        """Connect via WebSocket transport."""
        # WebSocket support would require additional WS client library
        logger.error(f"WebSocket transport not yet implemented for {self.name}")
        return False

    async def _load_server_info(self) -> None:
        """Load server capabilities and info."""
        if not self._session:
            return
        try:
            self.capabilities = self._session.get_server_capabilities()
        except Exception as e:
            logger.warning(f"Could not load server info for {self.name}: {e}")

    async def _load_tools(self) -> None:
        """Load available tools from the MCP server."""
        if not self._session:
            return
        try:
            tools_result = await self._session.list_tools()
            self.tools = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema,
                }
                for t in (tools_result.tools or [])
            ]
        except Exception as e:
            logger.warning(f"Could not load tools for {self.name}: {e}")

    async def list_tools(self) -> list[dict]:
        """List available tools."""
        if self.status != "connected":
            return []
        return self.tools

    async def call_tool(
        self, 
        tool_name: str, 
        arguments: dict,
        timeout_ms: int = 60000
    ) -> McpToolResult:
        """
        Call an MCP tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            timeout_ms: Timeout in milliseconds
            
        Returns:
            McpToolResult with content or error
        """
        if self.status != "connected" or not self._session:
            return McpToolResult(
                is_error=True,
                error=f"Not connected to server {self.name}"
            )
        
        try:
            # Create timeout signal
            # async with asyncio.timeout(timeout_ms / 1000):
            result = await self._session.call_tool(
                tool_name, 
                arguments,
            )
            
            content = []
            for item in (result.content or []):
                if hasattr(item, "text") and item.text is not None:
                    content.append({"type": "text", "text": item.text})
                elif hasattr(item, "data") and item.data is not None:
                    content.append({"type": "text", "text": str(item.data)})
                elif hasattr(item, "type"):
                    content.append({
                        "type": item.type, 
                        "data": vars(item) if hasattr(item, "__dict__") else {}
                    })
            
            return McpToolResult(content=content)
            
        except asyncio.TimeoutError:
            return McpToolResult(
                is_error=True,
                error=f"Tool call timed out after {timeout_ms}ms"
            )
        except Exception as e:
            logger.error(f"Tool call failed for {self.name}.{tool_name}: {e}")
            return McpToolResult(
                is_error=True,
                error=str(e)
            )

    async def list_resources(self) -> list[dict]:
        """List available resources."""
        if self.status != "connected" or not self._session:
            return []
        try:
            resources_result = await self._session.list_resources()
            self.resources = [
                {
                    "uri": r.uri,
                    "name": r.name,
                    "description": r.description or "",
                    "mimeType": getattr(r, "mimeType", None),
                }
                for r in (resources_result.resources or [])
            ]
        except Exception as e:
            logger.warning(f"Could not load resources for {self.name}: {e}")
        return self.resources

    async def read_resource(self, uri: str) -> dict:
        """
        Read a resource by URI.
        
        Args:
            uri: Resource URI to read
            
        Returns:
            Resource contents or error
        """
        if self.status != "connected" or not self._session:
            return {"error": f"Not connected to server {self.name}"}
        
        try:
            result = await self._session.read_resource(uri)
            contents = []
            for item in (result.contents or []):
                if hasattr(item, "text") and item.text is not None:
                    contents.append({"type": "text", "text": item.text})
                elif hasattr(item, "blob") and item.blob is not None:
                    contents.append({"type": "blob", "blob": item.blob})
                elif hasattr(item, "type"):
                    contents.append({"type": item.type, "data": vars(item)})
            return {"contents": contents}
        except Exception as e:
            logger.error(f"Read resource failed for {uri}: {e}")
            return {"error": str(e)}

    async def list_prompts(self) -> list[dict]:
        """List available prompts."""
        if self.status != "connected" or not self._session:
            return []
        try:
            prompts_result = await self._session.list_prompts()
            return [
                {
                    "name": p.name,
                    "description": p.description or "",
                    "arguments": getattr(p, "arguments", None),
                }
                for p in (prompts_result.prompts or [])
            ]
        except Exception as e:
            logger.warning(f"Could not load prompts for {self.name}: {e}")
            return []

    async def get_prompt(self, name: str, arguments: dict | None = None) -> dict:
        """Get a prompt by name with optional arguments."""
        if self.status != "connected" or not self._session:
            return {"error": f"Not connected to server {self.name}"}
        
        try:
            result = await self._session.get_prompt(name, arguments or {})
            messages = []
            for msg in (result.messages or []):
                messages.append({
                    "role": msg.role if hasattr(msg, "role") else "user",
                    "content": vars(msg.content) if hasattr(msg, "content") else {},
                })
            return {"messages": messages}
        except Exception as e:
            logger.error(f"Get prompt failed for {name}: {e}")
            return {"error": str(e)}

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        self.status = "disconnected"
        self._session = None
        
        if self._cleanup:
            try:
                await self._cleanup.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error during cleanup for {self.name}: {e}")
        
        self._read_stream = None
        self._write_stream = None


class McpService:
    """
    Service for managing MCP server connections.
    
    Provides:
    - Server configuration management
    - Connection lifecycle management
    - Tool call forwarding
    - Resource management
    """
    
    def __init__(self):
        self._servers: dict[str, McpServerConfig] = {}
        self._connections: dict[str, McpClient] = {}
        self._server_configs: dict[str, dict] = {}  # Raw config storage

    def add_server(self, config: McpServerConfig) -> None:
        """Register an MCP server configuration."""
        self._servers[config.name] = config
        self._server_configs[config.name] = {
            "name": config.name,
            "transport": config.transport,
            "command": config.command,
            "args": config.args,
            "env": config.env,
            "url": config.url,
            "headers": config.headers,
        }

    def get_server(self, name: str) -> McpServerConfig | None:
        """Get server configuration by name."""
        return self._servers.get(name)

    def list_servers(self) -> list[dict]:
        """List all registered server configurations."""
        return [
            {
                "name": s.name,
                "transport": s.transport,
                "command": s.command,
                "url": s.url,
            }
            for s in self._servers.values()
        ]

    async def connect(self, name: str) -> bool:
        """
        Connect to an MCP server.
        
        Args:
            name: Server name
            
        Returns:
            True if connection successful
        """
        config = self._servers.get(name)
        if not config:
            logger.error(f"Server {name} not found in configuration")
            return False
        
        # Disconnect existing connection if any
        if name in self._connections:
            await self.disconnect(name)
        
        client = McpClient(name, config)
        success = await client.connect()
        
        if success:
            self._connections[name] = client
        else:
            client.status = "failed"
            self._connections[name] = client  # Store for error tracking
        
        return success

    async def disconnect(self, name: str) -> None:
        """Disconnect from an MCP server."""
        if name in self._connections:
            await self._connections[name].disconnect()
            del self._connections[name]

    def get_connection(self, name: str) -> McpClient | None:
        """Get active connection by name."""
        return self._connections.get(name)

    def list_connections(self) -> list[str]:
        """List connected server names."""
        return list(self._connections.keys())

    def get_connection_status(self, name: str) -> str:
        """Get connection status for a server."""
        client = self._connections.get(name)
        return client.status if client else "disconnected"

    async def call_mcp_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict,
    ) -> dict:
        """
        Call an MCP tool on a connected server.
        
        Args:
            server_name: Name of the connected server
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result dict
        """
        client = self._connections.get(server_name)
        if not client:
            return {"error": f"Server {server_name} not connected"}
        
        result = await client.call_tool(tool_name, arguments)
        if result.is_error:
            return {"error": result.error, "is_error": True}
        return {"content": result.content}

    async def list_mcp_resources(self, server_name: str) -> list[dict]:
        """List resources from a connected server."""
        client = self._connections.get(server_name)
        if not client:
            return []
        return await client.list_resources()

    async def read_mcp_resource(self, server_name: str, uri: str) -> dict:
        """Read a resource from a connected server."""
        client = self._connections.get(server_name)
        if not client:
            return {"error": f"Server {server_name} not connected"}
        return await client.read_resource(uri)

    def get_all_tools(self) -> list[dict]:
        """Get tools from all connected servers."""
        all_tools = []
        for name, client in self._connections.items():
            if client.status == "connected":
                for tool in client.tools:
                    all_tools.append({
                        **tool,
                        "server": name,
                        # Normalize tool name for this server
                        "normalized_name": f"mcp__{name}__{tool['name']}",
                    })
        return all_tools

    def get_all_resources(self) -> list[dict]:
        """Get resources from all connected servers."""
        all_resources = []
        for name, client in self._connections.items():
            if client.status == "connected":
                for resource in client.resources:
                    all_resources.append({
                        **resource,
                        "server": name,
                    })
        return all_resources


# Global service instance
_mcp_service: McpService | None = None


def get_mcp_service() -> McpService:
    """Get or create the global MCP service instance."""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = McpService()
    return _mcp_service


# Convenience functions

async def mcp_connect(server_name: str) -> dict:
    """Connect to an MCP server."""
    service = get_mcp_service()
    success = await service.connect(server_name)
    return {"success": success}


async def mcp_disconnect(server_name: str) -> dict:
    """Disconnect from an MCP server."""
    service = get_mcp_service()
    await service.disconnect(server_name)
    return {"success": True}


async def mcp_list_servers() -> list[dict]:
    """List all configured MCP servers."""
    service = get_mcp_service()
    return service.list_servers()


async def mcp_list_connections() -> list[dict]:
    """List connected MCP servers with status."""
    service = get_mcp_service()
    return [
        {"name": name, "status": service.get_connection_status(name)}
        for name in service.list_connections()
    ]


async def mcp_list_tools(server_name: str) -> list[dict]:
    """List tools available on a connected server."""
    service = get_mcp_service()
    client = service.get_connection(server_name)
    if not client:
        return []
    return await client.list_tools()


async def mcp_call_tool(
    server_name: str,
    tool_name: str,
    arguments: dict,
) -> dict:
    """Call an MCP tool."""
    service = get_mcp_service()
    return await service.call_mcp_tool(server_name, tool_name, arguments)


async def mcp_list_resources(server_name: str) -> list[dict]:
    """List resources from a connected server."""
    service = get_mcp_service()
    return await service.list_mcp_resources(server_name)


async def mcp_read_resource(server_name: str, uri: str) -> dict:
    """Read a resource from a connected server."""
    service = get_mcp_service()
    return await service.read_mcp_resource(server_name, uri)


def mcp_add_server(
    name: str,
    transport: str,
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    url: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    """Add an MCP server configuration."""
    try:
        transport_type = McpTransport(transport.lower())
    except ValueError:
        return {"error": f"Invalid transport type: {transport}"}
    
    config = McpServerConfig(
        name=name,
        transport=transport_type,
        command=command,
        args=args or [],
        env=env or {},
        url=url,
        headers=headers,
    )
    
    service = get_mcp_service()
    service.add_server(config)
    return {"success": True, "server": name}


def mcp_get_all_tools() -> list[dict]:
    """Get all tools from all connected servers."""
    service = get_mcp_service()
    return service.get_all_tools()


def mcp_get_all_resources() -> list[dict]:
    """Get all resources from all connected servers."""
    service = get_mcp_service()
    return service.get_all_resources()
