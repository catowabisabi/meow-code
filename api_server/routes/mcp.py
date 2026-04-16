"""
FastAPI routes for MCP server configuration.
"""
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/mcp", tags=["mcp"])

MCP_CONFIG_PATH = Path.home() / ".claude" / "mcp_servers.json"


class MCPServer(BaseModel):
    name: str
    command: str
    args: Optional[list[str]] = None
    env: Optional[dict[str, str]] = None
    enabled: bool = True


class MCPServerCreate(BaseModel):
    name: str
    command: str
    args: Optional[list[str]] = None
    env: Optional[dict[str, str]] = None
    enabled: bool = True


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    command: Optional[str] = None
    args: Optional[list[str]] = None
    env: Optional[dict[str, str]] = None
    enabled: Optional[bool] = None


def _load_mcp_servers() -> list[dict]:
    try:
        if not MCP_CONFIG_PATH.exists():
            return []
        with open(MCP_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("servers", [])
    except (json.JSONDecodeError, IOError):
        return []


def _save_mcp_servers(servers: list[dict]) -> None:
    MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MCP_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"servers": servers}, f, ensure_ascii=False, indent=2)


@router.get("/servers")
async def list_mcp_servers():
    servers = _load_mcp_servers()
    return {"servers": servers, "count": len(servers)}


@router.post("/servers")
async def create_mcp_server(data: MCPServerCreate):
    if not data.name or not data.command:
        raise HTTPException(status_code=400, detail="name and command are required")

    servers = _load_mcp_servers()
    if any(s.get("name") == data.name for s in servers):
        raise HTTPException(status_code=409, detail="Server with this name already exists")

    servers.append({
        "name": data.name,
        "command": data.command,
        "args": data.args or [],
        "env": data.env or {},
        "enabled": data.enabled,
    })
    _save_mcp_servers(servers)
    return {"ok": True, "server": data}


@router.put("/servers/{name}")
async def update_mcp_server(name: str, data: MCPServerUpdate):
    servers = _load_mcp_servers()
    idx = next((i for i, s in enumerate(servers) if s.get("name") == name), None)

    if idx is None:
        raise HTTPException(status_code=404, detail="Server not found")

    update_data = data.model_dump(exclude_unset=True)
    servers[idx].update(update_data)
    _save_mcp_servers(servers)
    return {"ok": True}


@router.delete("/servers/{name}")
async def delete_mcp_server(name: str):
    servers = _load_mcp_servers()
    original_len = len(servers)
    servers = [s for s in servers if s.get("name") != name]

    if len(servers) == original_len:
        raise HTTPException(status_code=404, detail="Server not found")

    _save_mcp_servers(servers)
    return {"ok": True}


@router.patch("/servers/{name}/enable")
async def enable_mcp_server(name: str, enabled: bool):
    servers = _load_mcp_servers()
    idx = next((i for i, s in enumerate(servers) if s.get("name") == name), None)

    if idx is None:
        raise HTTPException(status_code=404, detail="Server not found")

    servers[idx]["enabled"] = enabled
    _save_mcp_servers(servers)
    return {"ok": True, "enabled": enabled}


@router.get("/templates")
async def get_mcp_templates():
    templates = [
        {
            "name": "filesystem",
            "label": "Filesystem",
            "description": "Read, write, and manage files on your computer",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        },
        {
            "name": "github",
            "label": "GitHub",
            "description": "Interact with GitHub repositories, issues, and pull requests",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
        },
        {
            "name": "slack",
            "label": "Slack",
            "description": "Send messages and manage channels in Slack",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-slack"],
        },
        {
            "name": "postgres",
            "label": "PostgreSQL",
            "description": "Query and manage PostgreSQL databases",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres"],
        },
        {
            "name": "brave-search",
            "label": "Brave Search",
            "description": "Search the web using Brave Search API",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        },
        {
            "name": "google-maps",
            "label": "Google Maps",
            "description": "Get location details, directions, and distance calculations",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-google-maps"],
        },
        {
            "name": "sentry",
            "label": "Sentry",
            "description": "Retrieve and manage issues from Sentry",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sentry"],
        },
        {
            "name": "aws-kb-retrieval",
            "label": "AWS KB Retrieval",
            "description": "Query AWS Knowledge Base for Bedrock",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-aws-kb-retrieval-server"],
        },
    ]
    return {"templates": templates}
