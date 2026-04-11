"""
Brief Tool — enable brief mode for concise responses.
"""
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


async def execute_brief(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """
    Execute brief tool - enables or disables brief mode.
    """
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    enabled = args.get('enabled', True)
    max_length = args.get('max_length', None)
    
    result_parts = [f"Brief mode {'enabled' if enabled else 'disabled'}"]
    
    if enabled and max_length is not None:
        result_parts.append(f" (max length: {max_length} words)")
    elif enabled:
        result_parts.append(" (using default max length)")
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output="".join(result_parts),
        is_error=False,
    )


TOOL_BRIEF = ToolDef(
    name="brief",
    description="Enable brief mode for concise responses",
    input_schema={
        "type": "object",
        "properties": {
            "enabled": {"type": "boolean", "default": True},
            "max_length": {"type": "number", "description": "Max response length in words"},
        },
    },
    is_read_only=False,
    risk_level="low",
    execute=execute_brief,
)


__all__ = ["TOOL_BRIEF"]