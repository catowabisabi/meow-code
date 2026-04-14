"""Notion integration tool.

Based on TypeScript NotionTool implementation.
Provides Notion page creation and search capabilities.
"""
import os
from typing import Any, Dict

import httpx

from .types import ToolDef, ToolContext, ToolResult

NOTION_API_VERSION = "2022-06-28"
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")

TIMEOUT = 30.0
CONNECT_TIMEOUT = 10.0
MAX_OUTPUT_SIZE = 30000


def _get_api_key() -> str:
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY environment variable is not set")
    return NOTION_API_KEY


def _make_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


async def _post(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{NOTION_API_BASE}{endpoint}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT, connect=CONNECT_TIMEOUT)) as client:
        response = await client.post(url, headers=_make_headers(), json=data)
        response.raise_for_status()
        return response.json()


async def _get(endpoint: str) -> Dict[str, Any]:
    url = f"{NOTION_API_BASE}{endpoint}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT, connect=CONNECT_TIMEOUT)) as client:
        response = await client.get(url, headers=_make_headers())
        response.raise_for_status()
        return response.json()


async def _patch(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{NOTION_API_BASE}{endpoint}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT, connect=CONNECT_TIMEOUT)) as client:
        response = await client.patch(url, headers=_make_headers(), json=data)
        response.raise_for_status()
        return response.json()


async def _delete(endpoint: str) -> Dict[str, Any]:
    url = f"{NOTION_API_BASE}{endpoint}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT, connect=CONNECT_TIMEOUT)) as client:
        response = await client.delete(url, headers=_make_headers())
        response.raise_for_status()
        return response.json()


def _truncate_output(data: Any) -> str:
    output = str(data)
    if len(output) > MAX_OUTPUT_SIZE:
        return output[:MAX_OUTPUT_SIZE] + "\n...(truncated)"
    return output


def _build_block(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert simplified block input to Notion block format."""
    block_type = item.get("type", "paragraph")
    text = item.get("text", "")

    if block_type == "heading_1":
        return {
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }
    elif block_type == "heading_2":
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }
    elif block_type == "to_do":
        return {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": text}}],
                "checked": item.get("checked", False),
            },
        }
    elif block_type == "bulleted_list_item":
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }
    elif block_type == "code":
        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": text}}],
                "language": item.get("language", "plain text"),
            },
        }
    else:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }


async def _notion_search(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    try:
        query = args.get("query", "")
        obj_type = args.get("type")

        if not query:
            return ToolResult(tool_call_id=tool_call_id, output="query is required", is_error=True)

        data: Dict[str, Any] = {"query": query}
        if obj_type:
            data["filter"] = {"property": "object", "value": obj_type}

        result = await _post("/search", data)
        return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

    except ValueError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion API key error: {str(e)}", is_error=True)
    except httpx.HTTPStatusError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion API error: {e.response.status_code} {e.response.text}", is_error=True)
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion search error: {str(e)}", is_error=True)


notion_search_tool = ToolDef(
    name="notion_search",
    description="Search your Notion workspace for pages and databases by keyword.",
    input_schema={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "type": {"type": "string", "enum": ["page", "database"], "description": "Filter by object type (optional)"},
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=_notion_search,
)


async def _notion_read_page(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    try:
        page_id = args.get("pageId")
        if not page_id:
            return ToolResult(tool_call_id=tool_call_id, output="pageId is required", is_error=True)

        page = await _get(f"/pages/{page_id}")
        blocks = await _get(f"/blocks/{page_id}/children")

        result = {"page": page, "blocks": blocks}
        return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

    except ValueError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion API key error: {str(e)}", is_error=True)
    except httpx.HTTPStatusError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion API error: {e.response.status_code} {e.response.text}", is_error=True)
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion read error: {str(e)}", is_error=True)


notion_read_page_tool = ToolDef(
    name="notion_read_page",
    description="Read a Notion page: its properties and content blocks. Returns the page metadata and all child blocks.",
    input_schema={
        "type": "object",
        "required": ["pageId"],
        "properties": {
            "pageId": {"type": "string", "description": "The Notion page ID (UUID format, with or without dashes)"},
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=_notion_read_page,
)


async def _notion_write_page(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    try:
        action = args.get("action")

        if action == "archive":
            page_id = args.get("pageId")
            if not page_id:
                return ToolResult(tool_call_id=tool_call_id, output="pageId is required for archive action", is_error=True)
            result = await _patch(f"/pages/{page_id}", {"archived": True})
            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        if action == "update":
            page_id = args.get("pageId")
            if not page_id:
                return ToolResult(tool_call_id=tool_call_id, output="pageId is required for update action", is_error=True)
            properties = args.get("properties", {})
            result = await _patch(f"/pages/{page_id}", {"properties": properties})
            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        if action == "create":
            parent_id = args.get("parentId")
            if not parent_id:
                return ToolResult(tool_call_id=tool_call_id, output="parentId is required for create action", is_error=True)

            parent_type = args.get("parentType", "page")
            title = args.get("title", "Untitled")

            properties = args.get("properties")
            if not properties:
                properties = {"title": {"title": [{"text": {"content": title}}]}}

            content_items = args.get("content", [])
            children = [_build_block(item) for item in content_items] if content_items else []

            if parent_type == "database":
                data = {"parent": {"database_id": parent_id}, "properties": properties}
                if children:
                    data["children"] = children
                result = await _post("/pages", data)
            else:
                data = {"parent": {"page_id": parent_id}, "properties": properties}
                if children:
                    data["children"] = children
                result = await _post("/pages", data)

            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        return ToolResult(tool_call_id=tool_call_id, output=f"Unknown action: {action}", is_error=True)

    except ValueError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion API key error: {str(e)}", is_error=True)
    except httpx.HTTPStatusError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion API error: {e.response.status_code} {e.response.text}", is_error=True)
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion write error: {str(e)}", is_error=True)


notion_write_page_tool = ToolDef(
    name="notion_write_page",
    description=(
        "Create or update a Notion page.\n"
        "For 'create': provide parentId (page or database), title, and optional content blocks.\n"
        "For 'update': provide pageId and properties to update.\n"
        "For 'archive': provide pageId to archive it.\n"
        "Content items can be: {type: 'paragraph'|'heading_1'|'heading_2'|'to_do'|'bulleted_list_item'|'code', text: '...', checked?: bool, language?: string}"
    ),
    input_schema={
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {"type": "string", "enum": ["create", "update", "archive"], "description": "Action to perform"},
            "parentId": {"type": "string", "description": "Parent page/database ID (for create)"},
            "parentType": {"type": "string", "enum": ["page", "database"], "description": "Parent type (default: page)"},
            "pageId": {"type": "string", "description": "Page ID (for update/archive)"},
            "title": {"type": "string", "description": "Page title (for create)"},
            "properties": {"type": "object", "description": "Page properties (Notion format)"},
            "content": {
                "type": "array",
                "description": "Content blocks to add",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "text": {"type": "string"},
                        "checked": {"type": "boolean"},
                        "language": {"type": "string"},
                    },
                },
            },
        },
    },
    is_read_only=False,
    risk_level="medium",
    execute=_notion_write_page,
)


async def _notion_database(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    try:
        action = args.get("action")

        if action == "get":
            database_id = args.get("databaseId")
            if not database_id:
                return ToolResult(tool_call_id=tool_call_id, output="databaseId is required for get action", is_error=True)
            result = await _get(f"/databases/{database_id}")
            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        if action == "query":
            database_id = args.get("databaseId")
            if not database_id:
                return ToolResult(tool_call_id=tool_call_id, output="databaseId is required for query action", is_error=True)
            filter_obj = args.get("filter")
            sorts = args.get("sorts")
            data: Dict[str, Any] = {}
            if filter_obj:
                data["filter"] = filter_obj
            if sorts:
                data["sorts"] = sorts
            result = await _post(f"/databases/{database_id}/query", data)
            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        if action == "create":
            parent_id = args.get("parentId")
            if not parent_id:
                return ToolResult(tool_call_id=tool_call_id, output="parentId is required for create action", is_error=True)
            title = args.get("title", "Untitled Database")
            properties = args.get("properties", {})

            data = {
                "parent": {"page_id": parent_id},
                "title": [{"text": {"content": title}}],
                "properties": properties,
            }
            result = await _post("/databases", data)
            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        return ToolResult(tool_call_id=tool_call_id, output=f"Unknown action: {action}", is_error=True)

    except ValueError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion API key error: {str(e)}", is_error=True)
    except httpx.HTTPStatusError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion API error: {e.response.status_code} {e.response.text}", is_error=True)
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion database error: {str(e)}", is_error=True)


notion_database_tool = ToolDef(
    name="notion_database",
    description=(
        "Query, get, or create Notion databases.\n"
        "'query': Query a database with optional filter and sorts.\n"
        "'get': Get database schema/properties.\n"
        "'create': Create a new database under a parent page."
    ),
    input_schema={
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {"type": "string", "enum": ["query", "get", "create"], "description": "Action"},
            "databaseId": {"type": "string", "description": "Database ID (for query/get)"},
            "filter": {"type": "object", "description": "Notion filter object (for query)"},
            "sorts": {"type": "array", "description": "Notion sorts array (for query)"},
            "parentId": {"type": "string", "description": "Parent page ID (for create)"},
            "title": {"type": "string", "description": "Database title (for create)"},
            "properties": {"type": "object", "description": "Database properties schema (for create)"},
        },
    },
    is_read_only=False,
    risk_level="medium",
    execute=_notion_database,
)


async def _notion_block(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    try:
        action = args.get("action")

        if action == "get":
            block_id = args.get("blockId")
            if not block_id:
                return ToolResult(tool_call_id=tool_call_id, output="blockId is required for get action", is_error=True)
            result = await _get(f"/blocks/{block_id}")
            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        if action == "list":
            block_id = args.get("blockId")
            if not block_id:
                return ToolResult(tool_call_id=tool_call_id, output="blockId is required for list action", is_error=True)
            result = await _get(f"/blocks/{block_id}/children")
            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        if action == "append":
            parent_id = args.get("parentId")
            if not parent_id:
                return ToolResult(tool_call_id=tool_call_id, output="parentId is required for append action", is_error=True)

            children_items = args.get("children", [])
            children = [_build_block(item) for item in children_items]

            result = await _patch(f"/blocks/{parent_id}/children", {"children": children})
            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        if action == "update":
            block_id = args.get("blockId")
            if not block_id:
                return ToolResult(tool_call_id=tool_call_id, output="blockId is required for update action", is_error=True)
            content = args.get("content", {})
            result = await _patch(f"/blocks/{block_id}", content)
            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        if action == "delete":
            block_id = args.get("blockId")
            if not block_id:
                return ToolResult(tool_call_id=tool_call_id, output="blockId is required for delete action", is_error=True)
            result = await _delete(f"/blocks/{block_id}")
            return ToolResult(tool_call_id=tool_call_id, output=_truncate_output(result), is_error=False)

        return ToolResult(tool_call_id=tool_call_id, output=f"Unknown action: {action}", is_error=True)

    except ValueError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion API key error: {str(e)}", is_error=True)
    except httpx.HTTPStatusError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion API error: {e.response.status_code} {e.response.text}", is_error=True)
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Notion block error: {str(e)}", is_error=True)


notion_block_tool = ToolDef(
    name="notion_block",
    description=(
        "Manage Notion blocks (content elements within pages).\n"
        "'get': Get a single block.\n"
        "'list': List child blocks of a page/block.\n"
        "'append': Append new blocks to a page/block.\n"
        "'update': Update an existing block.\n"
        "'delete': Delete a block."
    ),
    input_schema={
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {"type": "string", "enum": ["get", "list", "append", "update", "delete"], "description": "Action"},
            "blockId": {"type": "string", "description": "Block ID (for get/list/update/delete)"},
            "parentId": {"type": "string", "description": "Parent page/block ID (for append)"},
            "children": {
                "type": "array",
                "description": "Blocks to append (simplified: {type, text, checked?, language?})",
                "items": {"type": "object"},
            },
            "content": {"type": "object", "description": "Block content for update (raw Notion format)"},
        },
    },
    is_read_only=False,
    risk_level="medium",
    execute=_notion_block,
)


def register_notion_tools() -> None:
    from .executor import register_tool

    register_tool(notion_search_tool)
    register_tool(notion_read_page_tool)
    register_tool(notion_write_page_tool)
    register_tool(notion_database_tool)
    register_tool(notion_block_tool)


__all__ = [
    "notion_search_tool",
    "notion_read_page_tool",
    "notion_write_page_tool",
    "notion_database_tool",
    "notion_block_tool",
    "register_notion_tools",
]
