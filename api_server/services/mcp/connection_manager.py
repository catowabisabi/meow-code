"""
MCP Connection Manager for server lifecycle management.

Provides:
- Reconnection logic with exponential backoff
- Toggle enabled/disabled for MCP servers
- Connection state machine (pending, connected, failed, needs-auth, disabled)
- Batched state updates to reduce React re-renders
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set

from .client import (
    clear_server_cache,
    reconnect_mcp_server_impl,
)
from .config import (
    is_mcp_server_disabled,
    set_mcp_server_enabled,
)
from .mcp_types import (
    MCPServerConnection,
    ScopedMcpServerConfig,
    ServerResource,
)

logger = logging.getLogger(__name__)

MAX_RECONNECT_ATTEMPTS = 5
INITIAL_BACKOFF_MS = 1000
MAX_BACKOFF_MS = 30000
MCP_BATCH_FLUSH_MS = 16


class ConnectionState:
    """MCP server connection states."""
    PENDING = "pending"
    CONNECTED = "connected"
    FAILED = "failed"
    NEEDS_AUTH = "needs-auth"
    DISABLED = "disabled"


class ReconnectResult:
    """Result of a reconnection attempt."""
    def __init__(
        self,
        client: MCPServerConnection,
        tools: List[Any],
        commands: List[Any],
        resources: Optional[List[ServerResource]] = None,
    ):
        self.client = client
        self.tools = tools
        self.commands = commands
        self.resources = resources or []


class MCPConnectionManager:
    """
    Manages MCP server connections with automatic reconnection.
    
    Provides:
    - Reconnection with exponential backoff for remote transports
    - Toggle server enabled/disabled state
    - Batched state updates to coalesce rapid updates
    """
    
    def __init__(
        self,
        on_connection_attempt: Callable[[ReconnectResult], None],
    ):
        """
        Initialize the connection manager.
        
        Args:
            on_connection_attempt: Callback invoked with connection results
        """
        self._on_connection_attempt = on_connection_attempt
        self._reconnect_timers: Dict[str, asyncio.Task[None]] = {}
        self._pending_updates: List[Dict[str, Any]] = []
        self._flush_task: Optional[asyncio.Task[None]] = None
        self._channel_warned_kinds: Set[str] = set()
    
    def update_server(self, update: Dict[str, Any]) -> None:
        """
        Update server state, batching updates to reduce re-renders.
        
        Args:
            update: Server state update dict
        """
        self._pending_updates.append(update)
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_pending_updates())
    
    async def _flush_pending_updates(self) -> None:
        """Flush pending batched updates after a short delay."""
        await asyncio.sleep(MCP_BATCH_FLUSH_MS / 1000)
        if self._pending_updates:
            updates = self._pending_updates.copy()
            self._pending_updates.clear()
            for update in updates:
                self._on_connection_attempt(ReconnectResult(**update))
    
    async def reconnect_server(
        self,
        server_name: str,
        config: ScopedMcpServerConfig,
        get_client_fn: Callable[[str], Optional[MCPServerConnection]],
    ) -> None:
        """
        Attempt to reconnect a server with exponential backoff.
        
        Args:
            server_name: Name of the server to reconnect
            config: Server configuration
            get_client_fn: Function to get current client state
        """
        existing_timer = self._reconnect_timers.get(server_name)
        if existing_timer and not existing_timer.done():
            existing_timer.cancel()
            del self._reconnect_timers[server_name]
        
        if is_mcp_server_disabled(server_name):
            return
        
        client = get_client_fn(server_name)
        if not client:
            return
        
        config_type = config.get("type") if isinstance(config, dict) else getattr(config, 'type', None)
        if config_type in ("stdio", "sdk"):
            self.update_server({
                "client": {**vars(client), "type": ConnectionState.FAILED},
                "tools": [],
                "commands": [],
                "resources": [],
            })
            return
        
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            if is_mcp_server_disabled(server_name):
                return
            
            self.update_server({
                "client": {
                    **vars(client),
                    "type": ConnectionState.PENDING,
                    "reconnect_attempt": attempt,
                    "max_reconnect_attempts": MAX_RECONNECT_ATTEMPTS,
                },
                "tools": [],
                "commands": [],
                "resources": [],
            })
            
            try:
                result = await reconnect_mcp_server_impl(server_name, config)
                client_type = result.get("type") if isinstance(result, dict) else getattr(result, 'type', None)
                if client_type == ConnectionState.CONNECTED:
                    self._on_connection_attempt(result)
                    return
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt} failed: {e}")
            
            if attempt == MAX_RECONNECT_ATTEMPTS:
                self.update_server({
                    "client": {**vars(client), "type": ConnectionState.FAILED},
                    "tools": [],
                    "commands": [],
                    "resources": [],
                })
                return
            
            backoff_ms = min(INITIAL_BACKOFF_MS * (2 ** (attempt - 1)), MAX_BACKOFF_MS)
            await asyncio.sleep(backoff_ms / 1000)
    
    def cancel_reconnect(self, server_name: str) -> None:
        """Cancel pending reconnect for a server."""
        timer = self._reconnect_timers.get(server_name)
        if timer and not timer.done():
            timer.cancel()
            del self._reconnect_timers[server_name]
    
    def clear_channel_warned_kind(self, kind: str) -> None:
        """Clear a channel warning kind so the toast can show again."""
        self._channel_warned_kinds.discard(kind)


async def reconnect_mcp_server(
    server_name: str,
    config: ScopedMcpServerConfig,
    get_client_fn: Callable[[str], Optional[MCPServerConnection]],
) -> Optional[ReconnectResult]:
    """
    Reconnect a single MCP server with exponential backoff.
    
    Args:
        server_name: Name of the server
        config: Server configuration
        get_client_fn: Function to get current client state
    
    Returns:
        ReconnectResult if successful, None otherwise
    """
    if is_mcp_server_disabled(server_name):
        logger.debug(f"Server {server_name} is disabled, skipping reconnection")
        return None
    
    client = get_client_fn(server_name)
    if not client:
        return None
    
    config_type = config.get("type") if isinstance(config, dict) else getattr(config, 'type', None)
    if config_type in ("stdio", "sdk"):
        return ReconnectResult(
            client={**vars(client), "type": ConnectionState.FAILED} if hasattr(client, '__dict__') else client,
            tools=[],
            commands=[],
            resources=[],
        )
    
    for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
        if is_mcp_server_disabled(server_name):
            return None
        
        try:
            result = await reconnect_mcp_server_impl(server_name, config)
            if isinstance(result, dict):
                client_type = result.get("type")
            else:
                client_type = getattr(result, 'type', None)
            
            if client_type == ConnectionState.CONNECTED:
                return ReconnectResult(
                    client=result,
                    tools=result.get("tools", []) if isinstance(result, dict) else [],
                    commands=result.get("commands", []) if isinstance(result, dict) else [],
                    resources=result.get("resources", []) if isinstance(result, dict) else [],
                )
        except Exception as e:
            logger.error(f"Reconnection attempt {attempt} failed for {server_name}: {e}")
        
        if attempt == MAX_RECONNECT_ATTEMPTS:
            return ReconnectResult(
                client={**vars(client), "type": ConnectionState.FAILED} if hasattr(client, '__dict__') else client,
                tools=[],
                commands=[],
                resources=[],
            )
        
        backoff_ms = min(INITIAL_BACKOFF_MS * (2 ** (attempt - 1)), MAX_BACKOFF_MS)
        await asyncio.sleep(backoff_ms / 1000)
    
    return None


async def toggle_mcp_server(
    server_name: str,
    current_client: MCPServerConnection,
    on_connection_attempt: Callable[[ReconnectResult], None],
) -> None:
    """
    Toggle an MCP server between enabled and disabled states.
    
    Args:
        server_name: Name of the server
        current_client: Current client state
        on_connection_attempt: Callback for connection results
    """
    is_currently_disabled = current_client.type == ConnectionState.DISABLED
    
    if not is_currently_disabled:
        existing_timer = None
        if server_name in _active_reconnect_timers:
            existing_timer = _active_reconnect_timers[server_name]
            if existing_timer and not existing_timer.done():
                existing_timer.cancel()
        
        set_mcp_server_enabled(server_name, False)
        
        if current_client.type == ConnectionState.CONNECTED:
            config = current_client.config
            config_dict = vars(config) if hasattr(config, '__dict__') else (config or {})
            await clear_server_cache(server_name, config_dict)
        
        on_connection_attempt(ReconnectResult(
            client={
                "name": server_name,
                "type": ConnectionState.DISABLED,
                "config": config_dict,
            },
            tools=[],
            commands=[],
            resources=[],
        ))
    else:
        set_mcp_server_enabled(server_name, True)
        
        on_connection_attempt(ReconnectResult(
            client={
                "name": server_name,
                "type": ConnectionState.PENDING,
                "config": vars(current_client.config) if hasattr(current_client.config, '__dict__') else current_client.config,
            },
            tools=[],
            commands=[],
            resources=[],
        ))
        
        config = current_client.config
        config_dict = vars(config) if hasattr(config, '__dict__') else (config or {})
        result = await reconnect_mcp_server_impl(server_name, config_dict)
        on_connection_attempt(result)


_active_reconnect_timers: Dict[str, asyncio.Task[None]] = {}


async def schedule_reconnect_with_backoff(
    server_name: str,
    config: ScopedMcpServerConfig,
    get_client_fn: Callable[[str], Optional[MCPServerConnection]],
    on_connection_attempt: Callable[[ReconnectResult], None],
) -> None:
    """
    Schedule reconnection with exponential backoff.
    
    Args:
        server_name: Name of the server
        config: Server configuration
        get_client_fn: Function to get current client state
        on_connection_attempt: Callback for connection results
    """
    existing_timer = _active_reconnect_timers.get(server_name)
    if existing_timer and not existing_timer.done():
        existing_timer.cancel()
    
    async def reconnect_loop():
        if is_mcp_server_disabled(server_name):
            logger.debug(f"Server {server_name} disabled during reconnect, stopping")
            _active_reconnect_timers.pop(server_name, None)
            return
        
        client = get_client_fn(server_name)
        if not client:
            _active_reconnect_timers.pop(server_name, None)
            return
        
        config_type = config.get("type") if isinstance(config, dict) else getattr(config, 'type', None)
        transport_name = get_transport_display_name(config_type) if config_type else "SSE"
        
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            if is_mcp_server_disabled(server_name):
                logger.debug(f"Server {server_name} disabled during reconnect, stopping")
                return
            
            reconnect_result = ReconnectResult(
                client={
                    **({"name": server_name} if hasattr(client, '__dict__') else vars(client)),
                    "type": ConnectionState.PENDING,
                    "reconnect_attempt": attempt,
                    "max_reconnect_attempts": MAX_RECONNECT_ATTEMPTS,
                },
                tools=[],
                commands=[],
                resources=[],
            )
            on_connection_attempt(reconnect_result)
            
            start_time = asyncio.get_event_loop().time()
            try:
                result = await reconnect_mcp_server_impl(server_name, config)
                elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                if isinstance(result, dict):
                    result_type = result.get("type")
                else:
                    result_type = getattr(result, 'type', None)
                
                if result_type == ConnectionState.CONNECTED:
                    logger.debug(f"{transport_name} reconnection successful after {elapsed_ms:.0f}ms (attempt {attempt})")
                    _active_reconnect_timers.pop(server_name, None)
                    on_connection_attempt(result)
                    return
                
                logger.debug(f"{transport_name} reconnection attempt {attempt} completed with status: {result_type}")
                
                if attempt == MAX_RECONNECT_ATTEMPTS:
                    logger.debug(f"Max reconnection attempts ({MAX_RECONNECT_ATTEMPTS}) reached, giving up")
                    on_connection_attempt(ReconnectResult(
                        client={**({"name": server_name} if hasattr(client, '__dict__') else vars(client)), "type": ConnectionState.FAILED},
                        tools=[],
                        commands=[],
                        resources=[],
                    ))
                    return
            except Exception as e:
                elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                logger.error(f"{transport_name} reconnection attempt {attempt} failed after {elapsed_ms:.0f}ms: {e}")
                
                if attempt == MAX_RECONNECT_ATTEMPTS:
                    on_connection_attempt(ReconnectResult(
                        client={**({"name": server_name} if hasattr(client, '__dict__') else vars(client)), "type": ConnectionState.FAILED},
                        tools=[],
                        commands=[],
                        resources=[],
                    ))
                    return
            
            backoff_ms = min(INITIAL_BACKOFF_MS * (2 ** (attempt - 1)), MAX_BACKOFF_MS)
            logger.debug(f"Scheduling reconnection attempt {attempt + 1} in {backoff_ms}ms")
            await asyncio.sleep(backoff_ms / 1000)
        
        _active_reconnect_timers.pop(server_name, None)
    
    task = asyncio.create_task(reconnect_loop())
    _active_reconnect_timers[server_name] = task


def get_transport_display_name(transport_type: Optional[str]) -> str:
    """Get human-readable transport name."""
    if transport_type == "http":
        return "HTTP"
    elif transport_type in ("ws", "ws-ide"):
        return "WebSocket"
    return "SSE"


async def cleanup_connection_manager() -> None:
    """Cleanup all pending reconnection tasks."""
    for task in _active_reconnect_timers.values():
        if not task.done():
            task.cancel()
    _active_reconnect_timers.clear()