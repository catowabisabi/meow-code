"""
Pure utility functions for MCP name normalization.
This file has no dependencies to avoid circular imports.
"""

# Claude.ai server names are prefixed with this string
CLAUDEAI_SERVER_PREFIX = "claude.ai "


def normalize_name_for_mcp(name: str) -> str:
    """
    Normalize server names to be compatible with the API pattern ^[a-zA-Z0-9_-]{1,64}$
    Replaces any invalid characters (including dots and spaces) with underscores.

    For claude.ai servers (names starting with "claude.ai "), also collapses
    consecutive underscores and strips leading/trailing underscores to prevent
    interference with the __ delimiter used in MCP tool names.
    """
    normalized = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
    if name.startswith(CLAUDEAI_SERVER_PREFIX):
        # Collapse consecutive underscores and strip leading/trailing underscores
        while "__" in normalized:
            normalized = normalized.replace("__", "_")
        normalized = normalized.strip("_")
    return normalized
