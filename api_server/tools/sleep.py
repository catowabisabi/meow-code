"""
Sleep Tool — pauses execution for a specified duration.
"""
import asyncio
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


async def execute_sleep(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Execute sleep tool."""
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    seconds = args.get('seconds', 0)
    
    # Validate range
    if seconds < 0 or seconds > 300:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="seconds must be between 0 and 300",
            is_error=True,
        )
    
    # Check abort signal periodically
    try:
        remaining = seconds
        while remaining > 0:
            if ctx.abort_signal and ctx.abort_signal():
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=f"Sleep interrupted after {seconds - remaining:.1f}s",
                    is_error=False,
                )
            step = min(remaining, 0.1)  # Sleep in 100ms chunks
            await asyncio.sleep(step)
            remaining -= step
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Slept for {seconds}s",
            is_error=False,
        )
    except asyncio.CancelledError:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Sleep cancelled",
            is_error=False,
        )


TOOL_SLEEP = ToolDef(
    name="sleep",
    description="Wait for specified seconds",
    input_schema={
        "type": "object",
        "properties": {
            "seconds": {"type": "number", "minimum": 0, "maximum": 300},
        },
        "required": ["seconds"]
    },
    is_read_only=True,
    risk_level="low",
    execute=execute_sleep,
)


__all__ = ["TOOL_SLEEP"]