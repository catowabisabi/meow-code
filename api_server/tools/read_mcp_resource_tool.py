"""Read MCP resource tool.

Based on TypeScript ReadMcpResourceTool implementation.
Reads content from MCP server resources.
"""
from typing import Dict, Any

from .types import ToolDef, ToolContext, ToolResult
from ..services.mcp_service import mcp_read_resource


READ_MCP_RESOURCE_TOOL_NAME = "read_mcp_resource"


async def execute_read_mcp_resource(
    server: str,
    uri: str,
    ctx: ToolContext,
) -> Dict[str, Any]:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    if not server or not uri:
        return {
            "output": "Error: server and uri are required",
            "is_error": True,
        }
    
    result = await mcp_read_resource(server, uri)
    
    if "error" in result:
        return {
            "output": result["error"],
            "is_error": True,
        }
    
    contents = result.get("contents", [])
    if contents and isinstance(contents, list) and len(contents) > 0:
        first = contents[0]
        if isinstance(first, dict) and "text" in first:
            return {
                "output": first["text"],
                "is_error": False,
                "server": server,
                "uri": uri,
            }
    
    return {
        "output": str(result),
        "is_error": False,
        "server": server,
        "uri": uri,
    }


READ_MCP_RESOURCE_TOOL = ToolDef(
    name=READ_MCP_RESOURCE_TOOL_NAME,
    description="Read a resource from an MCP server by its URI. Returns the resource content.",
    input_schema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "MCP server name",
            },
            "uri": {
                "type": "string",
                "description": "Resource URI to read",
            },
        },
        "required": ["server", "uri"],
    },
    is_read_only=True,
    risk_level="low",
    execute=lambda args, ctx: execute_read_mcp_resource(
        args.get("server", ""),
        args.get("uri", ""),
        ctx,
    ),
)


__all__ = [
    "READ_MCP_RESOURCE_TOOL",
    "READ_MCP_RESOURCE_TOOL_NAME",
    "execute_read_mcp_resource",
]
