"""Send Message Tool - send messages to teammates or broadcast to team."""
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


async def _send_message(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    to = args.get("to", "")
    message = args.get("message", "")
    summary = args.get("summary")

    if not to:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'to' field is required",
            is_error=True,
        )

    if not message:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'message' field is required",
            is_error=True,
        )

    # Placeholder implementation - requires teammate system integration
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Message queued for delivery to {to}. Summary: {summary or 'No summary'}",
        is_error=False,
    )


async def _broadcast_message(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    message = args.get("message", "")
    summary = args.get("summary")

    if not message:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'message' field is required",
            is_error=True,
        )

    # Placeholder implementation - requires teammate system integration
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Message broadcast to team. Summary: {summary or 'No summary'}",
        is_error=False,
    )


SEND_MESSAGE_TOOL = ToolDef(
    name="send_message",
    description="Send a message to a specific teammate or broadcast to all teammates",
    input_schema={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient: teammate name, '*' for broadcast to all teammates",
            },
            "message": {
                "type": "string",
                "description": "Plain text message content",
            },
            "summary": {
                "type": "string",
                "description": "A 5-10 word summary shown as a preview in the UI",
            },
        },
        "required": ["to", "message"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=_send_message,
)


BROADCAST_MESSAGE_TOOL = ToolDef(
    name="broadcast_message",
    description="Broadcast a message to all teammates in the team",
    input_schema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Plain text message content to broadcast",
            },
            "summary": {
                "type": "string",
                "description": "A 5-10 word summary shown as a preview in the UI",
            },
        },
        "required": ["message"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=_broadcast_message,
)


__all__ = [
    "SEND_MESSAGE_TOOL",
    "BROADCAST_MESSAGE_TOOL",
]