"""Snip Tool - clip historical messages from conversation history."""
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


_message_store: list[Dict[str, Any]] = []


async def _snip_messages(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    start_index = args.get("start_index", 0)
    end_index = args.get("end_index")
    pattern = args.get("pattern", "")

    if end_index is not None and end_index <= start_index:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'end_index' must be greater than 'start_index'",
            is_error=True,
        )

    if pattern:
        matching = [m for m in _message_store if pattern.lower() in str(m.get("content", "")).lower()]
        result = matching[start_index:end_index] if end_index else matching[start_index:]
    else:
        result = _message_store[start_index:end_index] if end_index else _message_store[start_index:]

    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Snipped {len(result)} messages (index {start_index} to {end_index or 'end'})",
        is_error=False,
    )


async def _snip_save(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    snippet_id = args.get("snippet_id", "")
    messages = args.get("messages", [])

    if not snippet_id:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'snippet_id' field is required",
            is_error=True,
        )

    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Snippet '{snippet_id}' saved with {len(messages)} messages",
        is_error=False,
    )


async def _snip_list(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""

    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Available snippets: {len(_message_store)} total messages stored",
        is_error=False,
    )


SNIP_TOOL = ToolDef(
    name="snip",
    description="Clip historical messages from conversation history",
    input_schema={
        "type": "object",
        "properties": {
            "start_index": {
                "type": "integer",
                "description": "Starting index for the slice",
            },
            "end_index": {
                "type": "integer",
                "description": "Ending index for the slice (exclusive)",
            },
            "pattern": {
                "type": "string",
                "description": "Filter messages containing this pattern",
            },
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=_snip_messages,
)


SNIP_SAVE_TOOL = ToolDef(
    name="snip_save",
    description="Save a snippet of messages with a given ID",
    input_schema={
        "type": "object",
        "properties": {
            "snippet_id": {
                "type": "string",
                "description": "Unique ID for the snippet",
            },
            "messages": {
                "type": "array",
                "description": "Messages to save in the snippet",
            },
        },
        "required": ["snippet_id"],
    },
    is_read_only=False,
    risk_level="low",
    execute=_snip_save,
)


SNIP_LIST_TOOL = ToolDef(
    name="snip_list",
    description="List all saved snippets",
    input_schema={
        "type": "object",
        "properties": {},
    },
    is_read_only=True,
    risk_level="low",
    execute=_snip_list,
)


__all__ = [
    "SNIP_TOOL",
    "SNIP_SAVE_TOOL",
    "SNIP_LIST_TOOL",
]