"""
Sleep Tool — pauses execution for a specified duration.
"""
import asyncio
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


async def _sleep_execute(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Execute sleep tool."""
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    duration_ms = args.get('duration', 1000)  # default 1 second
    
    # Check abort signal periodically
    try:
        # Convert to seconds for sleep
        sleep_duration = duration_ms / 1000.0
        # Use sleep in small increments to check abort
        remaining = sleep_duration
        while remaining > 0:
            if ctx.abort_signal and ctx.abort_signal():
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=f"Sleep interrupted after {sleep_duration - remaining:.1f}s",
                    is_error=False,
                )
            step = min(remaining, 0.1)  # Sleep in 100ms chunks
            await asyncio.sleep(step)
            remaining -= step
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Slept for {sleep_duration}s",
            is_error=False,
        )
    except asyncio.CancelledError:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Sleep cancelled",
            is_error=False,
        )


SLEEP_TOOL = ToolDef(
    name="sleep",
    description="Wait for a specified duration. The user can interrupt the sleep at any time. Use when the user tells you to sleep or rest, or when you're waiting for something.",
    input_schema={
        "type": "object",
        "properties": {
            "duration": {
                "type": "number",
                "description": "Duration to sleep in milliseconds (default: 1000)",
            },
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=_sleep_execute,
)


__all__ = ["SLEEP_TOOL"]
