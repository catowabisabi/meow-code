"""
Pure string utility functions for MCP tool/server name parsing.

This file has no heavy dependencies to keep it lightweight for
consumers that only need string parsing (e.g., permissionValidation).
"""

from typing import Optional

from .normalization import normalize_name_for_mcp


def mcp_info_from_string(tool_string: str) -> Optional[dict]:
    """
    Extracts MCP server information from a tool name string.

    Args:
        tool_string: The string to parse. Expected format: "mcp__serverName__toolName"

    Returns:
        A dict with server_name and optional tool_name, or None if not a valid MCP rule

    Known limitation: If a server name contains "__", parsing will be incorrect.
    """
    parts = tool_string.split("__")
    if len(parts) < 3 or parts[0] != "mcp":
        return None
    server_name = parts[1]
    tool_name = "__".join(parts[2:]) if len(parts) > 2 else None
    return {"server_name": server_name, "tool_name": tool_name}


def get_mcp_prefix(server_name: str) -> str:
    """
    Generates the MCP tool/command name prefix for a given server.

    Args:
        server_name: Name of the MCP server

    Returns:
        The prefix string
    """
    return f"mcp__{normalize_name_for_mcp(server_name)}__"


def build_mcp_tool_name(server_name: str, tool_name: str) -> str:
    """
    Builds a fully qualified MCP tool name from server and tool names.

    Args:
        server_name: Name of the MCP server (unnormalized)
        tool_name: Name of the tool (unnormalized)

    Returns:
        The fully qualified name, e.g., "mcp__server__tool"
    """
    return f"{get_mcp_prefix(server_name)}{normalize_name_for_mcp(tool_name)}"


def get_tool_name_for_permission_check(tool: dict) -> str:
    """
    Returns the name to use for permission rule matching.

    For MCP tools, uses the fully qualified mcp__server__tool name so that
    deny rules targeting builtins (e.g., "Write") don't match unprefixed MCP
    replacements that share the same display name. Falls back to tool.name.

    Args:
        tool: Dict with name and optional mcp_info

    Returns:
        The name to use for permission checking
    """
    if tool.get("mcp_info"):
        return build_mcp_tool_name(
            tool["mcp_info"]["server_name"],
            tool["mcp_info"]["tool_name"]
        )
    return tool["name"]


def get_mcp_display_name(full_name: str, server_name: str) -> str:
    """
    Extracts the display name from an MCP tool/command name.

    Args:
        full_name: The full MCP tool/command name (e.g., "mcp__server_name__tool_name")
        server_name: The server name to remove from the prefix

    Returns:
        The display name without the MCP prefix
    """
    prefix = f"mcp__{normalize_name_for_mcp(server_name)}__"
    return full_name.replace(prefix, "")


def extract_mcp_tool_display_name(user_facing_name: str) -> str:
    """
    Extracts just the tool/command display name from a userFacingName.

    Args:
        user_facing_name: The full user-facing name (e.g., "github - Add comment to issue (MCP)")

    Returns:
        The display name without server prefix and (MCP) suffix
    """
    without_suffix = user_facing_name.replace("(MCP)", "").strip()
    dash_index = without_suffix.find(" - ")
    if dash_index != -1:
        return without_suffix[dash_index + 3:].strip()
    return without_suffix
