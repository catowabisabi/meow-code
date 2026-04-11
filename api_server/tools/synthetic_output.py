"""Synthetic output tool - generates structured JSON output."""
import json
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


async def execute_synthetic_output(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Execute synthetic output tool."""
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    data = args.get('data')
    schema = args.get('schema')
    
    if data is None:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="data is required",
            is_error=True,
        )
    
    # Format the output as JSON
    try:
        output = json.dumps(data, indent=2)
        if schema:
            output += f"\n\nSchema: {json.dumps(schema, indent=2)}"
        return ToolResult(
            tool_call_id=tool_call_id,
            output=output,
            is_error=False,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Failed to serialize output: {e}",
            is_error=True,
        )


TOOL_SYNTHETIC_OUTPUT = ToolDef(
    name="synthetic_output",
    description="Return structured JSON output",
    input_schema={
        "type": "object",
        "properties": {
            "data": {"type": "object"},
            "schema": {"type": "object"},
        },
        "required": ["data"]
    },
    is_read_only=True,
    risk_level="low",
    execute=execute_synthetic_output,
)


__all__ = ["TOOL_SYNTHETIC_OUTPUT"]