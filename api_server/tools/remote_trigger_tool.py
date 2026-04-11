"""Remote Trigger Tool - manage scheduled remote agent triggers."""
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


async def _remote_trigger(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    action = args.get("action", "")
    trigger_id = args.get("trigger_id")
    body = args.get("body", {})

    if action not in ["list", "get", "create", "update", "run"]:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Invalid action '{action}'. Must be one of: list, get, create, update, run",
            is_error=True,
        )

    if action in ["get", "update", "run"] and not trigger_id:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: action '{action}' requires trigger_id",
            is_error=True,
        )

    if action in ["create", "update"] and not body:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: action '{action}' requires body",
            is_error=True,
        )

    result_parts = [f"RemoteTrigger action: {action}"]
    if trigger_id:
        result_parts.append(f"trigger_id: {trigger_id}")
    if body:
        result_parts.append(f"body: {str(body)[:100]}")

    return ToolResult(
        tool_call_id=tool_call_id,
        output=" | ".join(result_parts),
        is_error=False,
    )


REMOTE_TRIGGER_TOOL = ToolDef(
    name="remote_trigger",
    description="Manage scheduled remote agent triggers (list, get, create, update, run)",
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "get", "create", "update", "run"],
                "description": "The action to perform",
            },
            "trigger_id": {
                "type": "string",
                "description": "Required for get, update, and run actions",
            },
            "body": {
                "type": "object",
                "description": "JSON body for create and update actions",
            },
        },
        "required": ["action"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=_remote_trigger,
)


__all__ = [
    "REMOTE_TRIGGER_TOOL",
]