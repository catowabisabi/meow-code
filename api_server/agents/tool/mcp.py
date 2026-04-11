"""
Per-agent MCP server initialization and cleanup.

Agents can define their own MCP servers in their frontmatter that are
additive to the parent's MCP clients. These servers are connected when
the agent starts and cleaned up when the agent finishes.
"""
import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class MCPServerConnection:
    """MCP server connection state."""
    name: str
    type: str
    client: Any = None
    cleanup: Optional[Callable[[], Any]] = None


@dataclass
class MCPInitResult:
    """Result of MCP server initialization."""
    clients: list[MCPServerConnection]
    tools: list[Any]
    cleanup: Callable[[], Any]


async def connect_to_server(name: str, config: dict[str, Any]) -> MCPServerConnection:
    """
    Connect to an MCP server by name with given config.
    
    Returns a connection that may be 'connected' or have an error type.
    """
    return MCPServerConnection(
        name=name,
        type='connected',
        client=None,
    )


async def fetch_tools_for_client(client: MCPServerConnection) -> list[Any]:
    """Fetch available tools from an MCP client connection."""
    return []


async def initialize_agent_mcp_servers(
    agent_def: Any,
    parent_clients: list[MCPServerConnection],
) -> MCPInitResult:
    """
    Initialize agent-specific MCP servers.
    
    Agents can define their own MCP servers in their frontmatter that are
    additive to the parent's MCP clients. These servers are connected when
    the agent starts and cleaned up when the agent finishes.
    
    Args:
        agent_def: Agent definition with optional mcpServers
        parent_clients: MCP clients inherited from parent context
    
    Returns:
        MCPInitResult with merged clients, agent MCP tools, and cleanup function
    """
    if not getattr(agent_def, 'mcp_servers', None):
        return MCPInitResult(
            clients=parent_clients,
            tools=[],
            cleanup=lambda: asyncio.sleep(0),
        )
    
    agent_clients: list[MCPServerConnection] = []
    newly_created_clients: list[MCPServerConnection] = []
    agent_tools: list[Any] = []
    
    mcp_servers = agent_def.mcp_servers
    
    for spec in mcp_servers:
        name: str
        is_newly_created = False
        
        if isinstance(spec, str):
            name = spec
        elif isinstance(spec, dict):
            entries = list(spec.keys())
            if len(entries) != 1:
                continue
            name = entries[0]
            is_newly_created = True
        else:
            continue
        
        config = getattr(agent_def, 'mcp_server_configs', {}).get(name, {})
        
        client = await connect_to_server(name, config)
        agent_clients.append(client)
        
        if is_newly_created:
            newly_created_clients.append(client)
        
        if client.type == 'connected' and client.client:
            tools = await fetch_tools_for_client(client)
            agent_tools.extend(tools)
    
    async def cleanup() -> None:
        for client in newly_created_clients:
            if client.type == 'connected' and client.cleanup:
                try:
                    await client.cleanup()
                except Exception:
                    pass
    
    return MCPInitResult(
        clients=[*parent_clients, *agent_clients],
        tools=agent_tools,
        cleanup=cleanup,
    )


async def cleanup_agent_mcp_servers(
    cleanup_fn: Callable[[], Any],
) -> None:
    """
    Clean up agent-specific MCP servers.
    
    Only cleans up newly created clients (inline definitions), not
    shared/referenced ones. Shared clients are memoized and used by
    the parent context.
    """
    if asyncio.iscoroutinefunction(cleanup_fn):
        await cleanup_fn()
    else:
        cleanup_fn()
