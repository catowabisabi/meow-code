"""
MCP Connection Management.

Manages MCP server connections, reconnection logic, and state updates.
This module provides a complete implementation of the useManageMCPConnections
hook from TypeScript, ported to Python for the api_server.

Key features:
- Server connection lifecycle (connect, disconnect, reconnect)
- Batch connection updates
- Connection state tracking per server
- Reconnection logic with backoff
- Server capability caching
- Connection health checks
- Graceful shutdown handling
- Event emission for connection changes
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Union,
)

from .client import (
    clear_server_cache,
    connect_to_server,
    fetch_prompts_for_client,
    fetch_resources_for_client,
    fetch_tools_for_client,
    reconnect_mcp_server_impl,
)
from .config import (
    does_enterprise_mcp_config_exist,
    filter_mcp_servers_by_policy,
    get_claude_code_mcp_configs,
    is_mcp_server_disabled,
    set_mcp_server_enabled,
)
from .normalization import normalize_name_for_mcp
from .mcp_types import (
    ConnectedMCPServer,
    FailedMCPServer,
    MCPServerConnection,
    NeedsAuthMCPServer,
    PendingMCPServer,
    ScopedMcpServerConfig,
    ServerCapabilities,
    ServerResource,
)

logger = logging.getLogger(__name__)

# Constants for reconnection with exponential backoff
MAX_RECONNECT_ATTEMPTS = 5
INITIAL_BACKOFF_MS = 1000
MAX_BACKOFF_MS = 30000
MCP_BATCH_FLUSH_MS = 16

# Terminal connection errors that indicate permanent failures
_TERMINAL_CONNECTION_ERRORS = [
    "ECONNRESET",
    "ETIMEDOUT",
    "EPIPE",
    "EHOSTUNREACH",
    "ECONNREFUSED",
    "Body Timeout Error",
    "terminated",
    "SSE stream disconnected",
    "Failed to reconnect SSE stream",
    "Maximum reconnection attempts",
]


class ConnectionState(str, Enum):
    """MCP server connection states."""
    PENDING = "pending"
    CONNECTED = "connected"
    FAILED = "failed"
    NEEDS_AUTH = "needs-auth"
    DISABLED = "disabled"


class PluginErrorType(str, Enum):
    """Plugin error types."""
    CONNECTION_FAILED = "connection_failed"
    AUTH_FAILED = "auth_failed"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class PluginError:
    """Plugin error with metadata for deduplication."""
    type: str
    source: str
    message: str
    plugin: Optional[str] = None
    server_name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReconnectResult:
    """Result of a reconnection attempt with tools, commands, and resources."""
    client: Union[ConnectedMCPServer, FailedMCPServer, NeedsAuthMCPServer, PendingMCPServer, Dict[str, Any]]
    tools: List[Any] = field(default_factory=list)
    commands: List[Any] = field(default_factory=list)
    resources: List[ServerResource] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for callback."""
        return {
            "client": self.client,
            "tools": self.tools,
            "commands": self.commands,
            "resources": self.resources,
        }


@dataclass
class ServerStats:
    """Statistics for MCP server connections."""
    connected_count: int = 0
    failed_count: int = 0
    pending_count: int = 0
    disabled_count: int = 0


# Tool and Command types (mirroring TypeScript interfaces)

@dataclass
class Tool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    is_mcp: bool = False
    original_tool_name: Optional[str] = None


@dataclass
class Command:
    """MCP command/prompt definition."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


class MCPConnectionsManager:
    """
    Manages MCP server connections with automatic reconnection.
    
    This class provides comprehensive connection lifecycle management:
    - Server connection lifecycle (connect, disconnect, reconnect)
    - Batch connection updates
    - Connection state tracking per server
    - Reconnection logic with exponential backoff
    - Server capability caching
    - Connection health checks
    - Graceful shutdown handling
    - Event emission for connection changes
    
    Example:
        manager = MCPConnectionsManager(on_connection_attempt=my_callback)
        await manager.connect_server(server_config)
    """

    def __init__(
        self,
        on_connection_attempt: Callable[[ReconnectResult], None],
    ):
        """
        Initialize the connection manager.
        
        Args:
            on_connection_attempt: Callback invoked with connection results.
                                   Called when servers connect, disconnect,
                                   or change state.
        """
        self._on_connection_attempt = on_connection_attempt
        self._reconnect_timers: Dict[str, asyncio.Task[None]] = {}
        self._pending_updates: List[Dict[str, Any]] = []
        self._flush_task: Optional[asyncio.Task[None]] = None
        self._channel_warned_kinds: Set[str] = set()
        self._connection_callbacks: List[Callable[[str, str, Any], None]] = []
        self._health_check_tasks: Dict[str, asyncio.Task[None]] = {}
        self._server_capabilities: Dict[str, ServerCapabilities] = {}
        self._server_last_health_check: Dict[str, float] = {}

    def update_server(self, update: Dict[str, Any]) -> None:
        """
        Update server state, batching updates to reduce re-renders.
        
        Batches multiple updates arriving within MCP_BATCH_FLUSH_MS and
        flushes them together in a single callback invocation.
        
        Args:
            update: Server state update dict containing:
                - client: MCPServerConnection or dict with server info
                - tools: List of tools (optional)
                - commands: List of commands (optional)
                - resources: List of resources (optional)
        """
        self._pending_updates.append(update)
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_pending_updates())

    async def _flush_pending_updates(self) -> None:
        """Flush pending batched updates after a short delay."""
        await asyncio.sleep(MCP_BATCH_FLUSH_MS / 1000)
        
        if not self._pending_updates:
            return
            
        updates = self._pending_updates.copy()
        self._pending_updates.clear()
        
        for update in updates:
            self._on_connection_attempt(ReconnectResult(**update))

    def on_connection_change(self, callback: Callable[[str, str, Any], None]) -> None:
        """
        Register for connection change events.
        
        Args:
            callback: Function(server_name, event_type, data) called on changes.
                    event_type can be: 'connected', 'disconnected', 'reconnecting',
                    'failed', 'disabled', 'tools_updated', 'commands_updated',
                    'resources_updated'
        """
        self._connection_callbacks.append(callback)

    def _emit_connection_change(
        self,
        server_name: str,
        event_type: str,
        data: Any,
    ) -> None:
        """Emit connection change event to all registered callbacks."""
        for callback in self._connection_callbacks:
            try:
                callback(server_name, event_type, data)
            except Exception as e:
                logger.warning(f"Error in connection change callback: {e}")

    async def connect_server(
        self,
        server_config: Union[ScopedMcpServerConfig, Dict[str, Any]],
        server_name: Optional[str] = None,
    ) -> ReconnectResult:
        """
        Connect to an MCP server.
        
        Args:
            server_config: Server configuration (dict or ScopedMcpServerConfig)
            server_name: Optional server name (defaults to config.name)
            
        Returns:
            ReconnectResult with connection status, tools, commands, resources
        """
        name = server_name or (
            server_config.get("name") 
            if isinstance(server_config, dict) 
            else getattr(server_config, "name", "unknown")
        )
        
        # Check if server is disabled
        if is_mcp_server_disabled(name):
            result = ReconnectResult(
                client={
                    "name": name,
                    "type": ConnectionState.DISABLED,
                    "config": server_config,
                },
                tools=[],
                commands=[],
                resources=[],
            )
            self._on_connection_attempt(result)
            return result
        
        # Set pending state
        self.update_server({
            "client": {
                "name": name,
                "type": ConnectionState.PENDING,
                "config": server_config,
            },
            "tools": [],
            "commands": [],
            "resources": [],
        })
        
        self._emit_connection_change(name, "reconnecting", {"config": server_config})
        
        try:
            # Connect to the server
            client_result = await connect_to_server(name, server_config)
            
            if client_result.type == "connected":
                # Fetch tools, commands, and resources
                tools = await fetch_tools_for_client(client_result)
                commands = await fetch_prompts_for_client(client_result)
                resources = await fetch_resources_for_client(client_result)
                
                # Cache capabilities
                if hasattr(client_result, 'capabilities') and client_result.capabilities:
                    self._server_capabilities[name] = client_result.capabilities
                
                result = ReconnectResult(
                    client=client_result,
                    tools=tools,
                    commands=commands,
                    resources=resources,
                )
                
                self._on_connection_attempt(result)
                self._emit_connection_change(name, "connected", {
                    "tools": len(tools),
                    "commands": len(commands),
                    "resources": len(resources),
                })
                
                # Set up onclose handler for reconnection
                if hasattr(client_result, 'client') and client_result.client:
                    self._setup_onclose_handler(name, server_config, client_result)
                
                return result
            else:
                # Connection failed or needs auth
                result = ReconnectResult(
                    client=client_result,
                    tools=[],
                    commands=[],
                    resources=[],
                )
                self._on_connection_attempt(result)
                
                if client_result.type == ConnectionState.NEEDS_AUTH:
                    self._emit_connection_change(name, "auth_required", {})
                else:
                    self._emit_connection_change(name, "failed", {
                        "error": getattr(client_result, 'error', 'Unknown error')
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to connect to server '{name}': {e}")
            result = ReconnectResult(
                client={
                    "name": name,
                    "type": ConnectionState.FAILED,
                    "config": server_config,
                    "error": str(e),
                },
                tools=[],
                commands=[],
                resources=[],
            )
            self._on_connection_attempt(result)
            self._emit_connection_change(name, "failed", {"error": str(e)})
            return result

    def _setup_onclose_handler(
        self,
        server_name: str,
        server_config: Any,
        client_result: ConnectedMCPServer,
    ) -> None:
        """
        Set up onclose handler for automatic reconnection.
        
        Args:
            server_name: Name of the server
            server_config: Server configuration
            client_result: Connected server result
        """
        config_type = (
            server_config.get("type")
            if isinstance(server_config, dict)
            else getattr(server_config, "type", None)
        )
        
        # Skip stdio (local process) and sdk (internal) - they don't support reconnection
        if config_type in ("stdio", "sdk"):
            return
        
        client = client_result.client if hasattr(client_result, 'client') else None
        if not client:
            return
        
        original_onclose = getattr(client, 'onclose', None)
        
        async def onclose_handler():
            """Handle connection close with automatic reconnection."""
            # Clear server cache
            try:
                await clear_server_cache(server_name, server_config)
            except Exception as e:
                logger.debug(f"Failed to invalidate server cache: {server_name}: {e}")
            
            # Check if server was disabled
            if is_mcp_server_disabled(server_name):
                logger.debug(f"Server {server_name} is disabled, skipping reconnection")
                return
            
            transport_name = get_transport_display_name(config_type)
            logger.debug(
                f"{transport_name} transport closed/disconnected for {server_name}, "
                f"attempting automatic reconnection"
            )
            
            # Cancel any existing reconnection attempt
            existing_timer = self._reconnect_timers.get(server_name)
            if existing_timer and not existing_timer.done():
                existing_timer.cancel()
                del self._reconnect_timers[server_name]
            
            # Start reconnection with backoff
            await self._reconnect_with_backoff(server_name, server_config)
        
        client.onclose = onclose_handler

    async def _reconnect_with_backoff(
        self,
        server_name: str,
        server_config: Any,
    ) -> None:
        """
        Reconnect with exponential backoff.
        
        Args:
            server_name: Name of the server
            server_config: Server configuration
        """
        async def reconnect_loop():
            config_type = (
                server_config.get("type")
                if isinstance(server_config, dict)
                else getattr(server_config, "type", None)
            )
            transport_name = get_transport_display_name(config_type)
            
            for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
                # Check if server was disabled while waiting
                if is_mcp_server_disabled(server_name):
                    logger.debug(f"Server {server_name} disabled during reconnection, stopping")
                    self._reconnect_timers.pop(server_name, None)
                    return
                
                # Update state to pending with reconnection attempt info
                self.update_server({
                    "client": {
                        "name": server_name,
                        "type": ConnectionState.PENDING,
                        "config": server_config,
                        "reconnect_attempt": attempt,
                        "max_reconnect_attempts": MAX_RECONNECT_ATTEMPTS,
                    },
                    "tools": [],
                    "commands": [],
                    "resources": [],
                })
                
                self._emit_connection_change(server_name, "reconnecting", {
                    "attempt": attempt,
                    "max_attempts": MAX_RECONNECT_ATTEMPTS,
                })
                
                reconnect_start_time = time.time()
                try:
                    result = await reconnect_mcp_server_impl(server_name, server_config)
                    elapsed_ms = (time.time() - reconnect_start_time) * 1000
                    
                    result_type = (
                        result.get("type")
                        if isinstance(result, dict)
                        else getattr(result, "type", None)
                    )
                    
                    if result_type == ConnectionState.CONNECTED:
                        logger.debug(
                            f"{transport_name} reconnection successful for {server_name} "
                            f"after {elapsed_ms:.0f}ms (attempt {attempt})"
                        )
                        self._reconnect_timers.pop(server_name, None)
                        
                        # Fetch tools, commands, resources
                        tools = await fetch_tools_for_client(result) if result_type == ConnectionState.CONNECTED else []
                        commands = await fetch_prompts_for_client(result) if result_type == ConnectionState.CONNECTED else []
                        resources = await fetch_resources_for_client(result) if result_type == ConnectionState.CONNECTED else []
                        
                        self._on_connection_attempt(ReconnectResult(
                            client=result,
                            tools=tools,
                            commands=commands,
                            resources=resources,
                        ))
                        self._emit_connection_change(server_name, "connected", {
                            "attempt": attempt,
                            "elapsed_ms": elapsed_ms,
                        })
                        
                        # Set up new onclose handler
                        if hasattr(result, 'client') and result.client:
                            self._setup_onclose_handler(server_name, server_config, result)
                        
                        return
                    
                    logger.debug(
                        f"{transport_name} reconnection attempt {attempt} for {server_name} "
                        f"completed with status: {result_type}"
                    )
                    
                    # On final attempt, update state with the result
                    if attempt == MAX_RECONNECT_ATTEMPTS:
                        logger.debug(
                            f"Max reconnection attempts ({MAX_RECONNECT_ATTEMPTS}) reached "
                            f"for {server_name}, giving up"
                        )
                        self._reconnect_timers.pop(server_name, None)
                        self._on_connection_attempt(ReconnectResult(
                            client={
                                "name": server_name,
                                "type": ConnectionState.FAILED,
                                "config": server_config,
                            },
                            tools=[],
                            commands=[],
                            resources=[],
                        ))
                        self._emit_connection_change(server_name, "failed", {
                            "reason": "max_attempts_reached",
                            "attempts": attempt,
                        })
                        return
                        
                except Exception as e:
                    elapsed_ms = (time.time() - reconnect_start_time) * 1000
                    logger.error(
                        f"{transport_name} reconnection attempt {attempt} for {server_name} "
                        f"failed after {elapsed_ms:.0f}ms: {e}"
                    )
                    
                    # On final attempt, mark as failed
                    if attempt == MAX_RECONNECT_ATTEMPTS:
                        logger.debug(
                            f"Max reconnection attempts ({MAX_RECONNECT_ATTEMPTS}) reached "
                            f"for {server_name}, giving up"
                        )
                        self._reconnect_timers.pop(server_name, None)
                        self.update_server({
                            "client": {
                                "name": server_name,
                                "type": ConnectionState.FAILED,
                                "config": server_config,
                            },
                            "tools": [],
                            "commands": [],
                            "resources": [],
                        })
                        self._emit_connection_change(server_name, "failed", {
                            "reason": "max_attempts_reached",
                            "error": str(e),
                        })
                        return
                
                # Schedule next retry with exponential backoff
                backoff_ms = min(INITIAL_BACKOFF_MS * (2 ** (attempt - 1)), MAX_BACKOFF_MS)
                logger.debug(
                    f"Scheduling reconnection attempt {attempt + 1} for {server_name} "
                    f"in {backoff_ms}ms"
                )
                await asyncio.sleep(backoff_ms / 1000)
            
            self._reconnect_timers.pop(server_name, None)
        
        task = asyncio.create_task(reconnect_loop())
        self._reconnect_timers[server_name] = task

    async def disconnect_server(self, server_name: str) -> None:
        """
        Disconnect from an MCP server.
        
        Args:
            server_name: Name of the server to disconnect
        """
        # Cancel any pending reconnection
        timer = self._reconnect_timers.get(server_name)
        if timer and not timer.done():
            timer.cancel()
            del self._reconnect_timers[server_name]
        
        # Cancel any health check
        health_task = self._health_check_tasks.get(server_name)
        if health_task and not health_task.done():
            health_task.cancel()
            del self._health_check_tasks[server_name]
        
        # Clear capabilities cache
        self._server_capabilities.pop(server_name, None)
        self._server_last_health_check.pop(server_name, None)
        
        self._emit_connection_change(server_name, "disconnected", {})

    async def reconnect_server(
        self,
        server_name: str,
        config: Union[ScopedMcpServerConfig, Dict[str, Any]],
    ) -> ReconnectResult:
        """
        Manually trigger reconnection for a server.
        
        This cancels any pending automatic reconnection and starts
        a fresh manual reconnection attempt.
        
        Args:
            server_name: Name of the server to reconnect
            config: Server configuration
            
        Returns:
            ReconnectResult with new connection status
        """
        # Cancel any pending automatic reconnection
        existing_timer = self._reconnect_timers.get(server_name)
        if existing_timer and not existing_timer.done():
            existing_timer.cancel()
            del self._reconnect_timers[server_name]
        
        self._emit_connection_change(server_name, "reconnecting", {"manual": True})
        
        try:
            result = await reconnect_mcp_server_impl(server_name, config)
            
            result_type = (
                result.get("type")
                if isinstance(result, dict)
                else getattr(result, "type", None)
            )
            
            if result_type == ConnectionState.CONNECTED:
                tools = await fetch_tools_for_client(result)
                commands = await fetch_prompts_for_client(result)
                resources = await fetch_resources_for_client(result)
                
                reconnect_result = ReconnectResult(
                    client=result,
                    tools=tools,
                    commands=commands,
                    resources=resources,
                )
                self._on_connection_attempt(reconnect_result)
                self._emit_connection_change(server_name, "connected", {})
                return reconnect_result
            else:
                reconnect_result = ReconnectResult(
                    client=result,
                    tools=[],
                    commands=[],
                    resources=[],
                )
                self._on_connection_attempt(reconnect_result)
                self._emit_connection_change(server_name, "failed", {
                    "type": result_type,
                })
                return reconnect_result
                
        except Exception as e:
            logger.error(f"Manual reconnection failed for {server_name}: {e}")
            result = ReconnectResult(
                client={
                    "name": server_name,
                    "type": ConnectionState.FAILED,
                    "config": config,
                    "error": str(e),
                },
                tools=[],
                commands=[],
                resources=[],
            )
            self._on_connection_attempt(result)
            self._emit_connection_change(server_name, "failed", {"error": str(e)})
            return result

    def get_connection_state(self, server_name: str) -> ConnectionState:
        """
        Get current connection state for a server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            ConnectionState enum value
        """
        capabilities = self._server_capabilities.get(server_name)
        if capabilities is None:
            return ConnectionState.PENDING
        return ConnectionState.CONNECTED

    def get_server_capabilities(self, server_name: str) -> Optional[ServerCapabilities]:
        """
        Get cached capabilities for a server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            ServerCapabilities if connected and cached, None otherwise
        """
        return self._server_capabilities.get(server_name)

    def is_server_connected(self, server_name: str) -> bool:
        """
        Check if a server is currently connected.
        
        Args:
            server_name: Name of the server
            
        Returns:
            True if server is connected, False otherwise
        """
        return server_name in self._server_capabilities

    async def toggle_server(
        self,
        server_name: str,
        current_state: Union[MCPServerConnection, Dict[str, Any]],
        config: Union[ScopedMcpServerConfig, Dict[str, Any]],
    ) -> ReconnectResult:
        """
        Toggle a server between enabled and disabled states.
        
        When disabling:
        - Cancels any pending reconnection
        - Persists disabled state to disk
        - Disconnects if currently connected
        
        When enabling:
        - Persists enabled state to disk
        - Sets state to pending
        - Initiates reconnection
        
        Args:
            server_name: Name of the server
            current_state: Current server state
            config: Server configuration
            
        Returns:
            ReconnectResult with new state
        """
        current_type = (
            current_state.get("type")
            if isinstance(current_state, dict)
            else getattr(current_state, "type", None)
        )
        is_currently_disabled = current_type == ConnectionState.DISABLED
        
        if not is_currently_disabled:
            # Disabling
            existing_timer = self._reconnect_timers.get(server_name)
            if existing_timer and not existing_timer.done():
                existing_timer.cancel()
                del self._reconnect_timers[server_name]
            
            # Persist disabled state to disk
            set_mcp_server_enabled(server_name, False)
            
            # Disconnect if connected
            if current_type == ConnectionState.CONNECTED:
                config_dict = config if isinstance(config, dict) else vars(config)
                await clear_server_cache(server_name, config_dict)
            
            # Update to disabled state
            result = ReconnectResult(
                client={
                    "name": server_name,
                    "type": ConnectionState.DISABLED,
                    "config": config,
                },
                tools=[],
                commands=[],
                resources=[],
            )
            self._on_connection_attempt(result)
            self._emit_connection_change(server_name, "disabled", {})
            return result
        else:
            # Enabling
            set_mcp_server_enabled(server_name, True)
            
            # Mark as pending
            result = ReconnectResult(
                client={
                    "name": server_name,
                    "type": ConnectionState.PENDING,
                    "config": config,
                },
                tools=[],
                commands=[],
                resources=[],
            )
            self._on_connection_attempt(result)
            self._emit_connection_change(server_name, "reconnecting", {"manual": True})
            
            # Reconnect
            try:
                reconnect_result = await self.reconnect_server(server_name, config)
                return reconnect_result
            except Exception as e:
                logger.error(f"Failed to reconnect {server_name}: {e}")
                return result

    async def refresh_server_tools(self, server_name: str) -> List[Any]:
        """
        Refresh tools for a connected server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            List of tools from the server
        """
        capabilities = self._server_capabilities.get(server_name)
        if not capabilities:
            return []
        
        try:
            # Create a temporary client-like object for fetching
            class TempClient:
                def __init__(self, name):
                    self.name = name
                    self.capabilities = capabilities
            
            temp_client = TempClient(server_name)
            temp_client.client = capabilities  # For compatibility
            
            tools = await fetch_tools_for_client(temp_client)
            self._emit_connection_change(server_name, "tools_updated", {
                "count": len(tools),
            })
            return tools
        except Exception as e:
            logger.error(f"Failed to refresh tools for {server_name}: {e}")
            return []

    async def refresh_server_resources(self, server_name: str) -> List[ServerResource]:
        """
        Refresh resources for a connected server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            List of resources from the server
        """
        capabilities = self._server_capabilities.get(server_name)
        if not capabilities:
            return []
        
        try:
            class TempClient:
                def __init__(self, name):
                    self.name = name
                    self.capabilities = capabilities
            
            temp_client = TempClient(server_name)
            temp_client.client = capabilities
            
            resources = await fetch_resources_for_client(temp_client)
            self._emit_connection_change(server_name, "resources_updated", {
                "count": len(resources),
            })
            return resources
        except Exception as e:
            logger.error(f"Failed to refresh resources for {server_name}: {e}")
            return []

    async def start_health_check(
        self,
        server_name: str,
        interval_seconds: float = 60.0,
    ) -> None:
        """
        Start periodic health checks for a server.
        
        Args:
            server_name: Name of the server
            interval_seconds: Interval between health checks
        """
        async def health_check_loop():
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    await self._perform_health_check(server_name)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"Health check error for {server_name}: {e}")
        
        task = asyncio.create_task(health_check_loop())
        self._health_check_tasks[server_name] = task

    async def stop_health_check(self, server_name: str) -> None:
        """
        Stop health checks for a server.
        
        Args:
            server_name: Name of the server
        """
        task = self._health_check_tasks.get(server_name)
        if task and not task.done():
            task.cancel()
            del self._health_check_tasks[server_name]

    async def _perform_health_check(self, server_name: str) -> bool:
        """
        Perform a health check on a server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            True if healthy, False otherwise
        """
        capabilities = self._server_capabilities.get(server_name)
        if not capabilities:
            return False
        
        self._server_last_health_check[server_name] = time.time()
        return True

    async def shutdown(self) -> None:
        """
        Graceful shutdown of all connection management.
        
        Cancels all pending reconnections, health checks, and flushes
        any pending batched updates.
        """
        # Cancel all reconnection timers
        for server_name, task in list(self._reconnect_timers.items()):
            if not task.done():
                task.cancel()
        self._reconnect_timers.clear()
        
        # Cancel all health check tasks
        for server_name, task in list(self._health_check_tasks.items()):
            if not task.done():
                task.cancel()
        self._health_check_tasks.clear()
        
        # Flush pending updates
        if self._flush_task and not self._flush_task.done():
            await asyncio.sleep(MCP_BATCH_FLUSH_MS / 1000)
            if self._pending_updates:
                updates = self._pending_updates.copy()
                self._pending_updates.clear()
                for update in updates:
                    self._on_connection_attempt(ReconnectResult(**update))


# Helper functions for MCP connection management

def get_mcp_prefix(server_name: str) -> str:
    """
    Get MCP tool prefix for a server.
    
    Args:
        server_name: Name of the server
        
    Returns:
        Prefix string like 'mcp__servername__'
    """
    return f"mcp__{normalize_name_for_mcp(server_name)}__"


def command_belongs_to_server(command: Dict[str, Any], server_name: str) -> bool:
    """
    Check if a command belongs to a specific server.
    
    Args:
        command: Command dict with optional 'server' key
        server_name: Name of the server
        
    Returns:
        True if command belongs to server
    """
    return command.get("server") == server_name


def get_transport_display_name(transport_type: Optional[str]) -> str:
    """
    Get human-readable transport name.
    
    Args:
        transport_type: Transport type string
        
    Returns:
        Human-readable name (HTTP, WebSocket, or SSE)
    """
    if transport_type == "http":
        return "HTTP"
    elif transport_type in ("ws", "ws-ide"):
        return "WebSocket"
    return "SSE"


def exclude_stale_plugin_clients(
    current_state: Dict[str, Any],
    configs: Dict[str, ScopedMcpServerConfig],
) -> Dict[str, List[Any]]:
    """
    Exclude stale plugin clients from state.
    
    A client is considered stale if:
    - It's not in the current configs
    - Its config scope is 'dynamic' (plugin-managed)
    
    Args:
        current_state: Current state dict with 'clients' key
        configs: Current server configurations
        
    Returns:
        Dict with 'stale' and 'clients' keys
    """
    clients = current_state.get("clients", [])
    stale = []
    active = []
    
    for client in clients:
        name = client.get("name")
        config = configs.get(name, {})
        scope = config.get("scope") if isinstance(config, dict) else getattr(config, "scope", None)
        
        if name in configs or scope != "dynamic":
            active.append(client)
        else:
            stale.append(client)
    
    return {"stale": stale, "clients": active}


def add_errors_to_app_state(
    existing_errors: List[PluginError],
    new_errors: List[PluginError],
) -> List[PluginError]:
    """
    Add errors to state, deduplicating to avoid showing the same error multiple times.
    
    Args:
        existing_errors: List of existing errors
        new_errors: List of new errors to add
        
    Returns:
        Combined list with duplicates removed
    """
    if not new_errors:
        return existing_errors
    
    existing_keys = {get_error_key(e) for e in existing_errors}
    unique_new = [e for e in new_errors if get_error_key(e) not in existing_keys]
    
    return existing_errors + unique_new


def get_error_key(error: PluginError) -> str:
    """
    Create a unique key for an error to enable deduplication.
    
    Args:
        error: PluginError instance
        
    Returns:
        Unique string key
    """
    plugin = error.plugin or "no-plugin"
    return f"{error.type}:{error.source}:{plugin}"


async def get_mcp_tools_commands_and_resources(
    on_connection_attempt: Callable[[ReconnectResult], None],
    configs: Dict[str, ScopedMcpServerConfig],
) -> None:
    """
    Get MCP tools, commands, and resources for all configured servers.
    
    This function initiates connections to all servers in the configs
    and reports connection results via the callback.
    
    Args:
        on_connection_attempt: Callback for connection results
        configs: Server name to config mapping
    """
    manager = MCPConnectionsManager(on_connection_attempt=on_connection_attempt)
    
    for server_name, config in configs.items():
        if is_mcp_server_disabled(server_name):
            continue
        
        await manager.connect_server(config, server_name)


async def initialize_servers_as_pending(
    configs: Dict[str, ScopedMcpServerConfig],
    current_clients: List[Any],
) -> List[Dict[str, Any]]:
    """
    Initialize servers to pending state if they don't exist.
    
    Compares current clients with configs and returns new client
    entries for servers that need to be added.
    
    Args:
        configs: Server configurations
        current_clients: Current client list
        
    Returns:
        List of new client entries to add
    """
    existing_names = {c.get("name") for c in current_clients}
    new_clients = []
    
    for name, config in configs.items():
        if name not in existing_names:
            client = {
                "name": name,
                "type": (
                    ConnectionState.DISABLED
                    if is_mcp_server_disabled(name)
                    else ConnectionState.PENDING
                ),
                "config": config,
            }
            new_clients.append(client)
    
    return new_clients


def is_terminal_connection_error(message: str) -> bool:
    """
    Check if error message indicates terminal connection failure.
    
    Terminal errors are those that indicate a permanent failure
    that should not trigger reconnection attempts.
    
    Args:
        message: Error message string
        
    Returns:
        True if error is terminal
    """
    return any(err in message for err in _TERMINAL_CONNECTION_ERRORS)


@dataclass
class PendingUpdate:
    """Represents a pending server state update."""
    client: Dict[str, Any]
    tools: Optional[List[Any]] = None
    commands: Optional[List[Any]] = None
    resources: Optional[List[ServerResource]] = None
    timestamp: float = field(default_factory=time.time)


class PendingUpdateBatcher:
    """
    Batches server state updates to coalesce rapid updates.
    
    Uses a time-based window (MCP_BATCH_FLUSH_MS) to batch updates
    arriving in quick succession.
    """
    
    def __init__(self, flush_callback: Callable[[List[PendingUpdate]], None]):
        """
        Initialize the batcher.
        
        Args:
            flush_callback: Called when batch is flushed with list of updates
        """
        self._flush_callback = flush_callback
        self._pending: List[PendingUpdate] = []
        self._flush_task: Optional[asyncio.Task[None]] = None
    
    def add(self, update: PendingUpdate) -> None:
        """
        Add an update to the batch.
        
        Args:
            update: PendingUpdate to add
        """
        self._pending.append(update)
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush())
    
    async def _flush(self) -> None:
        """Flush pending updates after the batch window."""
        await asyncio.sleep(MCP_BATCH_FLUSH_MS / 1000)
        if self._pending:
            updates = self._pending.copy()
            self._pending.clear()
            self._flush_callback(updates)
    
    async def flush_now(self) -> None:
        """Immediately flush all pending updates."""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        
        if self._pending:
            updates = self._pending.copy()
            self._pending.clear()
            self._flush_callback(updates)


# Channel notification support (KAIROS feature)

@dataclass
class ChannelMessage:
    """Channel message from MCP server."""
    content: str
    server_name: str
    meta: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)


class ChannelNotificationHandler:
    """
    Handles channel notifications from MCP servers.
    
    This enables servers to send messages to the Claude Code channel
    system for relay to the user.
    """
    
    def __init__(self):
        """Initialize the handler."""
        self._message_handlers: List[Callable[[ChannelMessage], None]] = []
        self._permission_handlers: Dict[str, Callable[[str, str], bool]] = {}
    
    def register_message_handler(
        self,
        handler: Callable[[ChannelMessage], None],
    ) -> None:
        """
        Register a handler for channel messages.
        
        Args:
            handler: Function to call with channel messages
        """
        self._message_handlers.append(handler)
    
    def register_permission_handler(
        self,
        request_id: str,
        handler: Callable[[str, str], bool],
    ) -> None:
        """
        Register a handler for permission replies.
        
        Args:
            request_id: Unique request identifier
            handler: Function(server_name, behavior) returning bool
        """
        self._permission_handlers[request_id] = handler
    
    def handle_message(self, message: ChannelMessage) -> None:
        """
        Handle an incoming channel message.
        
        Args:
            message: ChannelMessage to process
        """
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.warning(f"Error in channel message handler: {e}")
    
    def handle_permission_reply(
        self,
        request_id: str,
        behavior: str,
        server_name: str,
    ) -> bool:
        """
        Handle a permission reply.
        
        Args:
            request_id: Request identifier
            behavior: Behavior string from server
            server_name: Name of the server
            
        Returns:
            True if handler was found and returned True
        """
        handler = self._permission_handlers.pop(request_id, None)
        if handler:
            return handler(server_name, behavior)
        return False


# Notification schemas for list_changed events

TOOL_LIST_CHANGED_SCHEMA = "tools/list_changed"
PROMPT_LIST_CHANGED_SCHEMA = "prompts/list_changed"
RESOURCE_LIST_CHANGED_SCHEMA = "resources/list_changed"


class ListChangedHandler:
    """
    Handles list_changed notification handlers.
    
    Servers can notify when their tool, prompt, or resource lists change,
    allowing us to refresh cached data.
    """
    
    def __init__(
        self,
        on_tools_changed: Callable[[str], None] = None,
        on_prompts_changed: Callable[[str], None] = None,
        on_resources_changed: Callable[[str], None] = None,
    ):
        """
        Initialize the handler.
        
        Args:
            on_tools_changed: Callback(server_name) when tools list changes
            on_prompts_changed: Callback(server_name) when prompts list changes
            on_resources_changed: Callback(server_name) when resources list changes
        """
        self._on_tools_changed = on_tools_changed
        self._on_prompts_changed = on_prompts_changed
        self._on_resources_changed = on_resources_changed
    
    def handle_tools_changed(self, server_name: str) -> None:
        """Handle tools/list_changed notification."""
        if self._on_tools_changed:
            self._on_tools_changed(server_name)
    
    def handle_prompts_changed(self, server_name: str) -> None:
        """Handle prompts/list_changed notification."""
        if self._on_prompts_changed:
            self._on_prompts_changed(server_name)
    
    def handle_resources_changed(self, server_name: str) -> None:
        """Handle resources/list_changed notification."""
        if self._on_resources_changed:
            self._on_resources_changed(server_name)


# Analytics and logging helpers

def log_mcp_debug(server_name: str, message: str) -> None:
    """Log debug message for MCP server."""
    logger.debug(f"[{server_name}] {message}")


def log_mcp_error(server_name: str, message: str) -> None:
    """Log error message for MCP server."""
    logger.error(f"[{server_name}] {message}")


def log_mcp_info(server_name: str, message: str) -> None:
    """Log info message for MCP server."""
    logger.info(f"[{server_name}] {message}")


def log_mcp_warning(server_name: str, message: str) -> None:
    """Log warning message for MCP server."""
    logger.warning(f"[{server_name}] {message}")


# Error message utilities

def error_message(error: Exception) -> str:
    """
    Extract error message from exception.
    
    Args:
        error: Exception instance
        
    Returns:
        String error message
    """
    return str(error) or type(error).__name__


# Transport type checking

def is_remote_transport(config: Union[ScopedMcpServerConfig, Dict[str, Any]]) -> bool:
    """
    Check if config represents a remote transport.
    
    Remote transports (SSE, HTTP, WebSocket) support reconnection.
    Local transports (stdio, sdk) do not.
    
    Args:
        config: Server configuration
        
    Returns:
        True if remote transport
    """
    config_type = (
        config.get("type")
        if isinstance(config, dict)
        else getattr(config, "type", None)
    )
    return config_type in ("sse", "http", "ws", "ws-ide", "claudeai-proxy")


def is_local_transport(config: Union[ScopedMcpServerConfig, Dict[str, Any]]) -> bool:
    """
    Check if config represents a local transport.
    
    Args:
        config: Server configuration
        
    Returns:
        True if local transport
    """
    return not is_remote_transport(config)


# Cleanup utilities

async def cleanup_stale_connections(
    current_state: Dict[str, Any],
    configs: Dict[str, ScopedMcpServerConfig],
) -> List[str]:
    """
    Cleanup stale connections that are no longer in configs.
    
    Args:
        current_state: Current state with clients list
        configs: Current server configs
        
    Returns:
        List of cleaned up server names
    """
    cleaned = []
    stale_result = exclude_stale_plugin_clients(current_state, configs)
    
    for stale_client in stale_result.get("stale", []):
        name = stale_client.get("name")
        if name:
            try:
                await clear_server_cache(name, stale_client.get("config", {}))
                cleaned.append(name)
            except Exception as e:
                logger.debug(f"Failed to cleanup stale connection {name}: {e}")
    
    return cleaned


# Server counts for analytics

@dataclass
class ServerCounts:
    """Count of servers by scope."""
    enterprise: int = 0
    global_scope: int = 0
    project: int = 0
    user: int = 0
    plugin: int = 0
    claudeai: int = 0


def count_servers_by_scope(
    configs: Dict[str, ScopedMcpServerConfig],
) -> ServerCounts:
    """
    Count servers by their configuration scope.
    
    Args:
        configs: Server configurations
        
    Returns:
        ServerCounts with counts per scope
    """
    counts = ServerCounts()
    
    for name, config in configs.items():
        if isinstance(config, dict):
            scope = config.get("scope", "local")
        else:
            scope = getattr(config, "scope", "local")
        
        if scope == "enterprise":
            counts.enterprise += 1
        elif scope == "global":
            counts.global_scope += 1
        elif scope == "project":
            counts.project += 1
        elif scope == "local":
            counts.user += 1
        elif scope == "dynamic":
            counts.plugin += 1
        elif scope == "claudeai":
            counts.claudeai += 1
    
    return counts


def filter_enabled_configs(
    configs: Dict[str, ScopedMcpServerConfig],
) -> Dict[str, ScopedMcpServerConfig]:
    """
    Filter out disabled servers from configs.
    
    Args:
        configs: Server configurations
        
    Returns:
        Filtered configs without disabled servers
    """
    return {
        name: config
        for name, config in configs.items()
        if not is_mcp_server_disabled(name)
    }
