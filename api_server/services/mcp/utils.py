"""
MCP utility functions for tools, commands, and resources filtering.

Provides:
- Tool/command/resource filtering by MCP server
- Config hash computation for change detection
- MCP info extraction from tool names
- Config scope and file path utilities
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from .normalization import normalize_name_for_mcp
from .string_utils import get_mcp_prefix, mcp_info_from_string


def filter_tools_by_server(tools: List[Dict[str, Any]], server_name: str) -> List[Dict[str, Any]]:
    """
    Filter tools by MCP server name.
    
    Args:
        tools: Array of tools to filter
        server_name: Name of the MCP server
    
    Returns:
        Tools belonging to the specified server
    """
    prefix = get_mcp_prefix(server_name)
    return [t for t in tools if t.get("name", "").startswith(prefix)]


def filter_commands_by_server(commands: List[Dict[str, Any]], server_name: str) -> List[Dict[str, Any]]:
    """
    Filter commands by MCP server name.
    
    Args:
        commands: Array of commands to filter
        server_name: Name of the MCP server
    
    Returns:
        Commands belonging to the specified server
    """
    return [c for c in commands if command_belongs_to_server(c, server_name)]


def filter_mcp_prompts_by_server(
    commands: List[Dict[str, Any]],
    server_name: str,
) -> List[Dict[str, Any]]:
    """
    Filter MCP prompts (not skills) by server.
    
    Used by the /mcp menu capabilities display — skills are a separate
    feature shown in /skills, so they mustn't inflate the "prompts"
    capability badge.
    
    Args:
        commands: Array of commands to filter
        server_name: Name of the MCP server
    
    Returns:
        MCP prompts belonging to the specified server
    """
    return [
        c for c in commands
        if command_belongs_to_server(c, server_name)
        and not (c.get("type") == "prompt" and c.get("loadedFrom") == "mcp")
    ]


def filter_resources_by_server(
    resources: List[Dict[str, Any]],
    server_name: str,
) -> List[Dict[str, Any]]:
    """
    Filter resources by MCP server name.
    
    Args:
        resources: Array of resources to filter
        server_name: Name of the MCP server
    
    Returns:
        Resources belonging to the specified server
    """
    return [r for r in resources if r.get("server") == server_name]


def exclude_tools_by_server(tools: List[Dict[str, Any]], server_name: str) -> List[Dict[str, Any]]:
    """
    Remove tools belonging to a specific MCP server.
    
    Args:
        tools: Array of tools
        server_name: Name of the MCP server to exclude
    
    Returns:
        Tools not belonging to the specified server
    """
    prefix = get_mcp_prefix(server_name)
    return [t for t in tools if not t.get("name", "").startswith(prefix)]


def exclude_commands_by_server(
    commands: List[Dict[str, Any]],
    server_name: str,
) -> List[Dict[str, Any]]:
    """
    Remove commands belonging to a specific MCP server.
    
    Args:
        commands: Array of commands
        server_name: Name of the MCP server to exclude
    
    Returns:
        Commands not belonging to the specified server
    """
    return [c for c in commands if not command_belongs_to_server(c, server_name)]


def exclude_resources_by_server(
    resources: Dict[str, List[Dict[str, Any]]],
    server_name: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Remove resources belonging to a specific MCP server.
    
    Args:
        resources: Map of server resources
        server_name: Name of the MCP server to exclude
    
    Returns:
        Resources map without the specified server
    """
    result = {**resources}
    result.pop(server_name, None)
    return result


def command_belongs_to_server(command: Dict[str, Any], server_name: str) -> bool:
    """
    Check if a command belongs to a given MCP server.
    
    MCP **prompts** are named `mcp__<server>__<prompt>` (wire-format constraint);
    MCP **skills** are named `<server>:<skill>` (matching plugin/nested-dir skill
    naming). Both live in `mcp.commands`, so cleanup and filtering must match
    either shape.
    
    Args:
        command: Command to check
        server_name: Server name to match against
    
    Returns:
        True if the command belongs to the specified server
    """
    normalized = normalize_name_for_mcp(server_name)
    name = command.get("name")
    if not name:
        return False
    return name.startswith(f"mcp__{normalized}__") or name.startswith(f"{normalized}:")


def is_tool_from_mcp_server(tool_name: str, server_name: str) -> bool:
    """
    Check if a tool name belongs to a specific MCP server.
    
    Args:
        tool_name: The tool name to check
        server_name: The server name to match against
    
    Returns:
        True if the tool belongs to the specified server
    """
    info = mcp_info_from_string(tool_name)
    return info is not None and info.get("server_name") == server_name


def is_mcp_tool(tool: Dict[str, Any]) -> bool:
    """
    Check if a tool is from an MCP server.
    
    Args:
        tool: Tool to check
    
    Returns:
        True if the tool is from an MCP server
    """
    name = tool.get("name", "")
    return name.startswith("mcp__") or tool.get("isMcp") is True


def is_mcp_command(command: Dict[str, Any]) -> bool:
    """
    Check if a command is from an MCP server.
    
    Args:
        command: Command to check
    
    Returns:
        True if the command is from an MCP server
    """
    name = command.get("name", "")
    return name.startswith("mcp__") or command.get("isMcp") is True


def hash_mcp_config(config: Dict[str, Any]) -> str:
    """
    Compute a stable hash of an MCP server config for change detection.
    
    Excludes `scope` (provenance, not content — moving a server from .mcp.json
    to settings.json shouldn't reconnect it). Keys sorted so `{a:1,b:2}` and
    `{b:2,a:1}` hash the same.
    
    Args:
        config: MCP server config
    
    Returns:
        SHA256 hash (first 16 characters)
    """
    config_copy = {k: v for k, v in config.items() if k != "scope"}
    
    stable = json.dumps(config_copy, sort_keys=True, separators=(",", ":"))
    
    for key in sorted(config_copy.keys()):
        value = config_copy[key]
        if isinstance(value, dict):
            sorted_value = {k: config_copy[key][k] for k in sorted(config_copy[key].keys())}
            config_copy[key] = sorted_value
    
    stable = json.dumps(config_copy, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable.encode()).hexdigest()[:16]


def exclude_stale_plugin_clients(
    mcp_state: Dict[str, Any],
    configs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Remove stale MCP clients and their tools/commands/resources.
    
    A client is stale if:
    - scope 'dynamic' and name no longer in configs (plugin disabled), or
    - config hash changed (args/url/env edited in .mcp.json) — any scope
    
    The removal case is scoped to 'dynamic' so /reload-plugins can't
    accidentally disconnect a user-configured server that's just temporarily
    absent from the in-memory config (e.g. during a partial reload). The
    config-changed case applies to all scopes — if the config actually changed
    on disk, reconnecting is what you want.
    
    Args:
        mcp_state: Current MCP state with clients, tools, commands, resources
        configs: New configs to check against
    
    Returns:
        Updated state with stale clients removed, plus list of stale clients
    """
    clients = mcp_state.get("clients", [])
    tools = mcp_state.get("tools", [])
    commands = mcp_state.get("commands", [])
    resources = mcp_state.get("resources", {})
    
    stale = []
    for client in clients:
        client_name = client.get("name")
        fresh = configs.get(client_name)
        
        if not fresh:
            if client.get("config", {}).get("scope") == "dynamic":
                stale.append(client)
        elif hash_mcp_config(client.get("config", {})) != hash_mcp_config(fresh):
            stale.append(client)
    
    if not stale:
        return {**mcp_state, "stale": []}
    
    stale_names = {s.get("name") for s in stale}
    
    filtered_clients = [c for c in clients if c.get("name") not in stale_names]
    filtered_tools = tools
    filtered_commands = commands
    filtered_resources = {k: v for k, v in resources.items() if k not in stale_names}
    
    for s in stale:
        stale_name = s.get("name")
        filtered_tools = exclude_tools_by_server(filtered_tools, stale_name)
        filtered_commands = exclude_commands_by_server(filtered_commands, stale_name)
        filtered_resources = exclude_resources_by_server(filtered_resources, stale_name)
    
    return {
        "clients": filtered_clients,
        "tools": filtered_tools,
        "commands": filtered_commands,
        "resources": filtered_resources,
        "stale": stale,
    }


def get_mcp_server_scope_from_tool_name(tool_name: str) -> Optional[str]:
    """
    Get the scope/settings source for an MCP server from a tool name.
    
    Args:
        tool_name: MCP tool name (format: mcp__serverName__toolName)
    
    Returns:
        ConfigScope or None if not an MCP tool or server not found
    """
    if not is_mcp_tool({"name": tool_name}):
        return None
    
    mcp_info = mcp_info_from_string(tool_name)
    if not mcp_info:
        return None
    
    server_name = mcp_info.get("server_name", "")
    
    try:
        from .config import get_mcp_config_by_name
        server_config = get_mcp_config_by_name(server_name)
        
        if not server_config and server_name.startswith("claude_ai_"):
            return "claudeai"
        
        if isinstance(server_config, dict):
            return server_config.get("scope")
        elif hasattr(server_config, "scope"):
            return server_config.scope
    except Exception:
        pass
    
    return None


def parse_headers(header_array: List[str]) -> Dict[str, str]:
    """
    Parse HTTP headers from array of strings.
    
    Args:
        header_array: Array of "Header-Name: value" strings
    
    Returns:
        Dict of header name to value
    
    Raises:
        ValueError: If header format is invalid
    """
    headers: Dict[str, str] = {}
    
    for header in header_array:
        colon_index = header.index(":")
        if colon_index == -1:
            raise ValueError(f'Invalid header format: "{header}". Expected format: "Header-Name: value"')
        
        key = header[:colon_index].strip()
        value = header[colon_index + 1:].strip()
        
        if not key:
            raise ValueError(f'Invalid header: "{header}". Header name cannot be empty.')
        
        headers[key] = value
    
    return headers


def get_project_mcp_server_status(server_name: str) -> str:
    """
    Get the approval status of a project MCP server.
    
    Args:
        server_name: Name of the MCP server
    
    Returns:
        'approved', 'rejected', or 'pending'
    """
    try:
        from .config import get_settings
        settings = get_settings()
        normalized_name = normalize_name_for_mcp(server_name)
        
        if settings and settings.get("disabledMcpjsonServers"):
            disabled = settings.get("disabledMcpjsonServers", [])
            for name in disabled:
                if normalize_name_for_mcp(name) == normalized_name:
                    return "rejected"
        
        if settings and settings.get("enabledMcpjsonServers"):
            enabled = settings.get("enabledMcpjsonServers", [])
            for name in enabled:
                if normalize_name_for_mcp(name) == normalized_name:
                    return "approved"
        
        if settings and settings.get("enableAllProjectMcpServers"):
            return "approved"
    except Exception:
        pass
    
    return "pending"


def get_logging_safe_mcp_base_url(config: Dict[str, Any]) -> Optional[str]:
    """
    Extract MCP server base URL for analytics logging.
    
    Query strings are stripped because they can contain access tokens.
    Trailing slashes are also removed for normalization.
    Returns None for stdio/sdk servers or if URL parsing fails.
    
    Args:
        config: MCP server config
    
    Returns:
        Base URL without query string, or None
    """
    url = config.get("url") if isinstance(config, dict) else None
    if not url or not isinstance(url, str):
        return None
    
    try:
        parsed = json.loads(json.dumps({"url": url}))
        actual_url = parsed.get("url", url)
        
        if isinstance(actual_url, str):
            url_obj = URL(actual_url)
            url_obj.query = ""
            result = str(url_obj)
            if result.endswith("/"):
                result = result[:-1]
            return result
    except Exception:
        pass
    
    return None


class URL:
    """Simple URL parser for get_logging_safe_mcp_base_url."""
    def __init__(self, url: str):
        self.query = ""
        self._scheme = ""
        self._netloc = ""
        self._path = ""
        
        if "?" in url:
            url, self.query = url.split("?", 1)
        
        if "://" in url:
            self._scheme, rest = url.split("://", 1)
            if "/" in rest:
                self._netloc, self._path = rest.split("/", 1)
                self._path = "/" + self._path
            else:
                self._netloc = rest
    
    def __str__(self) -> str:
        result = f"{self._scheme}://{self._netloc}{self._path}"
        if self.query:
            result += f"?{self.query}"
        return result


def extract_agent_mcp_servers(
    agents: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Extract MCP server definitions from agent frontmatter.
    
    Groups them by server name with list of source agents.
    Only includes transport types supported by AgentMcpServerInfo.
    
    Args:
        agents: Array of agent definitions
    
    Returns:
        Array of AgentMcpServerInfo, grouped by server name
    """
    server_map: Dict[str, Dict[str, Any]] = {}
    
    for agent in agents:
        mcp_servers = agent.get("mcpServers", [])
        if not mcp_servers:
            continue
        
        for spec in mcp_servers:
            if isinstance(spec, str):
                continue
            
            entries = list(spec.items()) if isinstance(spec, dict) else []
            if len(entries) != 1:
                continue
            
            server_name, server_config = entries[0]
            
            if server_name in server_map:
                existing = server_map[server_name]
                source_agents = existing.get("sourceAgents", [])
                if agent.get("agentType") not in source_agents:
                    source_agents.append(agent.get("agentType"))
                existing["sourceAgents"] = source_agents
            else:
                config_with_name = {**server_config, "name": server_name}
                server_map[server_name] = {
                    "config": config_with_name,
                    "sourceAgents": [agent.get("agentType")],
                }
    
    result = []
    for name, data in server_map.items():
        config = data["config"]
        config_type = config.get("type") if isinstance(config, dict) else None
        
        entry: Dict[str, Any] = {
            "name": name,
            "sourceAgents": data["sourceAgents"],
        }
        
        if config_type is None or config_type == "stdio":
            entry["transport"] = "stdio"
            entry["command"] = config.get("command", "") if isinstance(config, dict) else ""
            entry["needsAuth"] = False
        elif config_type == "sse":
            entry["transport"] = "sse"
            entry["url"] = config.get("url", "") if isinstance(config, dict) else ""
            entry["needsAuth"] = True
        elif config_type == "http":
            entry["transport"] = "http"
            entry["url"] = config.get("url", "") if isinstance(config, dict) else ""
            entry["needsAuth"] = True
        elif config_type == "ws":
            entry["transport"] = "ws"
            entry["url"] = config.get("url", "") if isinstance(config, dict) else ""
            entry["needsAuth"] = False
        else:
            continue
        
        result.append(entry)
    
    return sorted(result, key=lambda x: x["name"])