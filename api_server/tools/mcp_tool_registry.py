"""
MCPTool - Tools for interacting with MCP (Model Context Protocol) servers.

Provides:
- Server listing and management
- Tool execution on MCP servers
- Resource access
- Authentication handling

Based on the TypeScript MCPTool implementation in _claude_code_leaked_source_code.
"""
import json
from dataclasses import dataclass

try:
    from ..services.mcp_service import (
        get_mcp_service,
        mcp_call_tool as svc_mcp_call_tool,
        mcp_list_tools as svc_mcp_list_tools,
        mcp_list_resources as svc_mcp_list_resources,
        mcp_read_resource as svc_mcp_read_resource,
    )
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from .types import ToolDef, ToolContext, ToolResult


TOOL_NAME = "mcp"


@dataclass
class MCPServerInfo:
    name: str
    status: str
    tools: list[str]
    resources: list[str]


async def _mcp_list_servers(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    if not HAS_MCP:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="MCP service not available",
            is_error=True,
        )
    
    try:
        service = get_mcp_service()
        servers = service.list_servers()
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "servers": servers,
            }),
            is_error=False,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error listing MCP servers: {str(e)}",
            is_error=True,
        )


async def _mcp_list_tools(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    if not HAS_MCP:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="MCP service not available",
            is_error=True,
        )
    
    server = args.get("server")
    
    try:
        if server:
            tools = await svc_mcp_list_tools(server)
        else:
            service = get_mcp_service()
            all_tools = {}
            servers = service.list_servers()
            for s in servers:
                try:
                    tools = await svc_mcp_list_tools(s["name"])
                    all_tools[s["name"]] = tools
                except Exception:
                    pass
            tools = all_tools
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "tools": tools,
            }),
            is_error=False,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error listing MCP tools: {str(e)}",
            is_error=True,
        )


async def _mcp_execute_tool(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    if not HAS_MCP:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="MCP service not available",
            is_error=True,
        )
    
    server = args.get("server", "")
    tool = args.get("tool", "")
    arguments = args.get("arguments", {})
    
    if not server or not tool:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: server and tool are required",
            is_error=True,
        )
    
    try:
        result = await svc_mcp_call_tool(server, tool, arguments)
        
        if "error" in result:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=result["error"],
                is_error=True,
            )
        
        content = result.get("content", [])
        if content and isinstance(content, list) and len(content) > 0:
            first = content[0]
            if isinstance(first, dict) and "text" in first:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=first["text"],
                    is_error=result.get("is_error", False),
                )
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps(result),
            is_error=result.get("is_error", False),
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error executing MCP tool: {str(e)}",
            is_error=True,
        )


async def _mcp_list_resources(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    if not HAS_MCP:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="MCP service not available",
            is_error=True,
        )
    
    server = args.get("server")
    
    try:
        if server:
            resources = await svc_mcp_list_resources(server)
        else:
            service = get_mcp_service()
            all_resources = service.get_all_resources()
            resources = all_resources
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "resources": resources,
            }),
            is_error=False,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error listing MCP resources: {str(e)}",
            is_error=True,
        )


async def _mcp_read_resource(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    if not HAS_MCP:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="MCP service not available",
            is_error=True,
        )
    
    server = args.get("server", "")
    uri = args.get("uri", "")
    
    if not server or not uri:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: server and uri are required",
            is_error=True,
        )
    
    try:
        result = await svc_mcp_read_resource(server, uri)
        
        if "error" in result:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=result["error"],
                is_error=True,
            )
        
        contents = result.get("contents", [])
        if contents and isinstance(contents, list) and len(contents) > 0:
            first = contents[0]
            if isinstance(first, dict) and "text" in first:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=first["text"],
                    is_error=False,
                )
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps(result),
            is_error=False,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error reading MCP resource: {str(e)}",
            is_error=True,
        )


LIST_MCP_SERVERS_TOOL = ToolDef(
    name="list_mcp_servers",
    description="List all connected MCP servers",
    input_schema={
        "type": "object",
        "properties": {},
    },
    is_read_only=True,
    risk_level="low",
    execute=_mcp_list_servers,
)


LIST_MCP_TOOLS_TOOL = ToolDef(
    name="list_mcp_tools",
    description="List tools available from MCP servers",
    input_schema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Optional MCP server name. If not provided, lists all servers.",
            },
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=_mcp_list_tools,
)


MCP_TOOL = ToolDef(
    name="mcp__tool",
    description="Execute a tool on a connected MCP server",
    input_schema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "MCP server name",
            },
            "tool": {
                "type": "string",
                "description": "Tool name on the MCP server",
            },
            "arguments": {
                "type": "object",
                "description": "Arguments to pass to the tool",
                "additionalProperties": True,
            },
        },
        "required": ["server", "tool"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=_mcp_execute_tool,
)


LIST_MCP_RESOURCES_TOOL = ToolDef(
    name="list_mcp_resources",
    description="List resources available from MCP servers",
    input_schema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Optional MCP server name",
            },
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=_mcp_list_resources,
)


READ_MCP_RESOURCE_TOOL = ToolDef(
    name="read_mcp_resource",
    description="Read a resource from an MCP server by URI",
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
    execute=_mcp_read_resource,
)


__all__ = [
    "LIST_MCP_SERVERS_TOOL",
    "LIST_MCP_TOOLS_TOOL",
    "MCP_TOOL",
    "LIST_MCP_RESOURCES_TOOL",
    "READ_MCP_RESOURCE_TOOL",
]
