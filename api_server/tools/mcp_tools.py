"""
MCP Tools - Tools for interacting with MCP servers.

Provides tools for:
- mcp__tool: Execute MCP tools on connected servers
- mcp__auth: MCP authentication handling
- list_mcp_resources: List resources from MCP servers
- read_mcp_resource: Read resources from MCP servers
"""
from typing import Any

from .types import ToolDef, ToolContext
from ..services.mcp_service import (
    get_mcp_service,
    mcp_call_tool as svc_mcp_call_tool,
    mcp_list_resources as svc_mcp_list_resources,
    mcp_read_resource as svc_mcp_read_resource,
)


TOOL_NAME = "mcp"


def mcp_tool_def(server_name: str) -> ToolDef:
    """Create tool definition for an MCP server."""
    return ToolDef(
        name=f"mcp_{server_name}",
        description=f"Execute MCP tool from server '{server_name}'",
        input_schema={
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "Name of the MCP tool to execute",
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments to pass to the MCP tool",
                    "additionalProperties": True,
                },
            },
            "required": ["tool_name", "arguments"],
        },
        is_read_only=False,
        risk_level="medium",
        execute=lambda args, ctx: _mcp_execute_wrapper(server_name, args, ctx),
    )


async def _mcp_execute_wrapper(server_name: str, args: dict, ctx: ToolContext) -> dict:
    """Wrapper for MCP tool execution."""
    tool_name = args.get("tool_name", "")
    arguments = args.get("arguments", {})
    return await execute_mcp_tool(server_name, tool_name, arguments, ctx)


async def execute_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: dict,
    ctx: ToolContext,
) -> dict:
    """Execute an MCP tool on a connected server."""
    result = await svc_mcp_call_tool(server_name, tool_name, arguments)
    
    if "error" in result:
        return {"output": result["error"], "is_error": True}
    
    content = result.get("content", [])
    if content and isinstance(content, list) and len(content) > 0:
        first = content[0]
        if isinstance(first, dict) and "text" in first:
            return {"output": first["text"], "is_error": result.get("is_error", False)}
    
    return {"output": str(result), "is_error": result.get("is_error", False)}


async def execute_mcp_auth(
    server_name: str,
    auth_type: str,
    credentials: dict,
    ctx: ToolContext,
) -> dict:
    """
    Handle MCP server authentication.
    
    Supports OAuth 2.0 and API key authentication.
    For OAuth, starts the flow and returns the authorization URL.
    """
    service = get_mcp_service()
    client = service.get_connection(server_name)
    
    if not client:
        server = service.get_server(server_name)
        if not server:
            return {"output": f"Server {server_name} not found", "is_error": True}
        
        if auth_type == "oauth":
            return await _start_oauth_flow(server_name, server, ctx)
        elif auth_type == "api_key":
            return {"output": f"Server {server_name} not connected. Connect first, then set API key.", "is_error": True}
        return {"output": f"Unknown auth type: {auth_type}", "is_error": True}
    
    if auth_type == "oauth":
        return await _start_oauth_flow(server_name, client.config, ctx)
    elif auth_type == "api_key":
        api_key = credentials.get("api_key")
        if not api_key:
            return {"output": "API key is required", "is_error": True}
        if hasattr(client, 'config') and hasattr(client.config, 'auth_token'):
            client.config.auth_token = api_key
        return {"output": f"API key configured for {server_name}", "is_error": False}
    
    return {"output": f"Unknown auth type: {auth_type}", "is_error": True}


async def _start_oauth_flow(server_name: str, server_config, ctx: ToolContext) -> dict:
    """
    Start OAuth flow for MCP server.
    
    Returns the authorization URL for user to complete authentication.
    """
    import asyncio
    from services.mcp.auth import MCPAuthProvider
    
    if hasattr(server_config, 'url'):
        server_url = server_config.url
    elif isinstance(server_config, dict):
        server_url = server_config.get("url", "")
    else:
        server_url = ""
    
    if not server_url:
        return {"output": f"Server {server_name} has no URL configured for OAuth", "is_error": True}
    
    auth_url_future: asyncio.Future = asyncio.get_event_loop().create_future()
    
    def on_auth_url(url: str) -> None:
        if not auth_url_future.done():
            auth_url_future.set_result(url)
    
    provider = MCPAuthProvider(
        server_name=server_name,
        server_config=server_config if isinstance(server_config, dict) else {},
        handle_redirection=False,
        on_authorization_url=on_auth_url,
    )
    
    asyncio.create_task(_run_oauth_flow(provider, server_config))
    
    try:
        auth_url = await asyncio.wait_for(auth_url_future, timeout=30.0)
        
        return {
            "output": f"OAuth authentication required for {server_name}.\n\nPlease visit this URL to authorize:\n\n{auth_url}\n\nOnce you complete authorization, the server will be reconnected automatically.",
            "is_error": False,
            "auth_url": auth_url,
        }
    except asyncio.TimeoutError:
        return {
            "output": f"OAuth flow timed out for {server_name}. Please try again.",
            "is_error": True,
        }
    except Exception as e:
        return {
            "output": f"Failed to start OAuth flow for {server_name}: {str(e)}",
            "is_error": True,
        }


async def _run_oauth_flow(provider: Any, server_config: Any) -> None:
    """
    Run the OAuth flow and handle completion.
    
    This runs in background after returning the auth URL to user.
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        oauth_state = await provider.state()
        code_verifier = await provider.code_verifier()
        await provider.save_code_verifier(code_verifier)
        
        auth_url = await _build_authorization_url(provider, server_config, oauth_state, code_verifier)
        
        if auth_url:
            await provider.redirect_to_authorization(auth_url)
            
    except Exception as e:
        logger.error(f"OAuth flow error: {e}")


async def _build_authorization_url(
    provider: Any,
    server_config: Any,
    state: str,
    code_verifier: str,
) -> str:
    """
    Build the OAuth authorization URL.
    
    Uses RFC 8628 or server-specific OAuth configuration.
    """
    # Get OAuth config from server
    oauth_config = None
    if isinstance(server_config, dict):
        oauth_config = server_config.get("oauth", {})
    elif hasattr(server_config, 'oauth'):
        oauth_config = server_config.oauth
    
    if not oauth_config:
        server_url = server_config.get("url") if isinstance(server_config, dict) else getattr(server_config, "url", "")
        if server_url:
            return f"{server_url.rstrip('/')}/oauth/authorize?state={state}"
        return ""
    
    auth_endpoint = oauth_config.get("auth_endpoint", "/oauth/authorize")
    client_id = oauth_config.get("client_id", "")
    redirect_uri = oauth_config.get("redirect_uri", "http://localhost:7778/api/mcp/auth/callback")
    scope = oauth_config.get("scope", "")
    
    import urllib.parse
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": _generate_code_challenge(code_verifier),
        "code_challenge_method": "S256",
    }
    if scope:
        params["scope"] = scope
    
    auth_endpoint = oauth_config.get("auth_endpoint", "/oauth/authorize")
    server_url = server_config.get("url") if isinstance(server_config, dict) else getattr(server_config, 'url', "")
    
    base_url = server_url.rstrip('/') if server_url else ""
    return f"{base_url}{auth_endpoint}?{urllib.parse.urlencode(params)}"


def _generate_code_challenge(code_verifier: str) -> str:
    """Generate PKCE code challenge from verifier."""
    import hashlib
    import base64
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


def mcp_auth_tool_def(server_name: str) -> ToolDef:
    """Create auth tool definition for an MCP server."""
    return ToolDef(
        name=f"mcp_{server_name}_auth",
        description=f"Authenticate with MCP server '{server_name}'",
        input_schema={
            "type": "object",
            "properties": {
                "auth_type": {
                    "type": "string",
                    "description": "Authentication type (oauth, api_key)",
                    "enum": ["oauth", "api_key"],
                },
                "credentials": {
                    "type": "object",
                    "description": "Authentication credentials",
                    "additionalProperties": True,
                },
            },
            "required": ["auth_type"],
        },
        is_read_only=False,
        risk_level="high",
        execute=lambda args, ctx: _mcp_auth_wrapper(server_name, args, ctx),
    )


async def _mcp_auth_wrapper(server_name: str, args: dict, ctx: ToolContext) -> dict:
    """Wrapper for MCP auth."""
    auth_type = args.get("auth_type", "")
    credentials = args.get("credentials", {})
    return await execute_mcp_auth(server_name, auth_type, credentials, ctx)


async def execute_list_mcp_resources(
    server: str | None,
    ctx: ToolContext,
) -> dict:
    """List MCP resources from a server."""
    if not server:
        service = get_mcp_service()
        all_resources = service.get_all_resources()
        return {"output": str(all_resources), "is_error": False}
    
    resources = await svc_mcp_list_resources(server)
    return {"output": str(resources), "is_error": False}


LIST_MCP_RESOURCES_TOOL = ToolDef(
    name="list_mcp_resources",
    description="List resources available from MCP servers",
    input_schema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Optional: MCP server name. If not provided, lists all resources.",
            },
        },
        "required": [],
    },
    is_read_only=True,
    risk_level="low",
    execute=lambda args, ctx: execute_list_mcp_resources(
        args.get("server"), ctx
    ),
)


async def execute_read_mcp_resource(
    server: str,
    uri: str,
    ctx: ToolContext,
) -> dict:
    """Read an MCP resource by URI."""
    if not server or not uri:
        return {"output": "Server and URI are required", "is_error": True}
    
    result = await svc_mcp_read_resource(server, uri)
    
    if "error" in result:
        return {"output": result["error"], "is_error": True}
    
    contents = result.get("contents", [])
    if contents and isinstance(contents, list) and len(contents) > 0:
        first = contents[0]
        if isinstance(first, dict) and "text" in first:
            return {"output": first["text"], "is_error": False}
    
    return {"output": str(result), "is_error": False}


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
    execute=lambda args, ctx: execute_read_mcp_resource(
        args.get("server"), args.get("uri"), ctx
    ),
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
    execute=lambda args, ctx: _mcp_generic_tool_wrapper(args, ctx),
)


async def _mcp_generic_tool_wrapper(args: dict, ctx: ToolContext) -> dict:
    """Wrapper for generic MCP tool calls."""
    server = args.get("server", "")
    tool = args.get("tool", "")
    arguments = args.get("arguments", {})
    
    if not server or not tool:
        return {"output": "Server and tool are required", "is_error": True}
    
    result = await svc_mcp_call_tool(server, tool, arguments)
    
    if "error" in result:
        return {"output": result["error"], "is_error": True}
    
    content = result.get("content", [])
    if content and isinstance(content, list) and len(content) > 0:
        first = content[0]
        if isinstance(first, dict) and "text" in first:
            return {"output": first["text"], "is_error": result.get("is_error", False)}
    
    return {"output": str(result), "is_error": result.get("is_error", False)}


MCP_AUTH_TOOL = ToolDef(
    name="mcp__auth",
    description="Authenticate with an MCP server",
    input_schema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "MCP server name",
            },
            "auth_type": {
                "type": "string",
                "description": "Authentication type (oauth, api_key)",
                "enum": ["oauth", "api_key"],
            },
            "credentials": {
                "type": "object",
                "description": "Authentication credentials",
                "additionalProperties": True,
            },
        },
        "required": ["server", "auth_type"],
    },
    is_read_only=False,
    risk_level="high",
    execute=lambda args, ctx: _mcp_auth_tool_wrapper(args, ctx),
)


async def _mcp_auth_tool_wrapper(args: dict, ctx: ToolContext) -> dict:
    """Wrapper for MCP auth tool."""
    server = args.get("server", "")
    auth_type = args.get("auth_type", "")
    credentials = args.get("credentials", {})
    
    if not server:
        return {"output": "Server is required", "is_error": True}
    
    return await execute_mcp_auth(server, auth_type, credentials, ctx)


def get_mcp_tools_for_server(server_name: str) -> list[ToolDef]:
    """Get all MCP tools for a specific server."""
    return [
        mcp_tool_def(server_name),
        mcp_auth_tool_def(server_name),
    ]


def get_all_mcp_tools() -> list[ToolDef]:
    """Get all MCP tools across all servers."""
    service = get_mcp_service()
    servers = service.list_servers()
    
    tools = [MCP_TOOL, MCP_AUTH_TOOL, LIST_MCP_RESOURCES_TOOL, READ_MCP_RESOURCE_TOOL]
    
    for server in servers:
        tools.extend(get_mcp_tools_for_server(server["name"]))
    
    return tools
