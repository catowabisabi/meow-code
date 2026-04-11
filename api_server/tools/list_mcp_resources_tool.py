from typing import Optional, Dict, Any

from .types import ToolDef, ToolContext, ToolResult
from ..services.mcp_service import get_mcp_service, mcp_list_resources


LIST_MCP_RESOURCES_TOOL_NAME = "list_mcp_resources"


async def execute_list_mcp_resources(
    server: Optional[str],
    ctx: ToolContext,
) -> Dict[str, Any]:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    if server:
        resources = await mcp_list_resources(server)
        return {
            "output": f"Resources from {server}: {resources}",
            "is_error": False,
            "server": server,
            "resources": resources,
        }
    
    service = get_mcp_service()
    all_resources = service.get_all_resources()
    
    return {
        "output": f"All MCP resources: {all_resources}",
        "is_error": False,
        "resources": all_resources,
    }


LIST_MCP_RESOURCES_TOOL = ToolDef(
    name=LIST_MCP_RESOURCES_TOOL_NAME,
    description="List resources available from MCP servers. Specify a server name to list resources from a specific server, or list all resources across all connected servers.",
    input_schema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Optional: MCP server name. If not provided, lists all resources from all servers.",
            },
        },
        "required": [],
    },
    is_read_only=True,
    risk_level="low",
    execute=lambda args, ctx: execute_list_mcp_resources(args.get("server"), ctx),
)


__all__ = [
    "LIST_MCP_RESOURCES_TOOL",
    "LIST_MCP_RESOURCES_TOOL_NAME",
    "execute_list_mcp_resources",
]
