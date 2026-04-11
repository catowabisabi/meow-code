"""Synthetic output tool - generates structured output."""
import json
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


async def _synthetic_output(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    content = args.get('content', '')
    format_type = args.get('format', 'text')
    
    if format_type == 'json':
        try:
            if isinstance(content, str):
                json.loads(content)
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Valid JSON: {content}",
                is_error=False,
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Invalid JSON: {e}",
                is_error=True,
            )
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=str(content),
        is_error=False,
    )


SYNTHETIC_OUTPUT_TOOL = ToolDef(
    name="synthetic_output",
    description="Generate structured output for the user.",
    input_schema={
        "type": "object",
        "properties": {
            "content": {"description": "Content to output"},
            "format": {"type": "string", "enum": ["text", "json", "markdown"], "description": "Output format"},
        },
        "required": ["content"],
    },
    is_read_only=True,
    risk_level="low",
    execute=_synthetic_output,
)


__all__ = ["SYNTHETIC_OUTPUT_TOOL"]
