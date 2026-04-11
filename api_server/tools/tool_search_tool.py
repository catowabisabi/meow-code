"""Tool search - search for available tools by name or description."""
import json
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult
from .executor import get_all_tools


async def _tool_search(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    query = args.get('query', '').lower()
    category = args.get('category')
    
    all_tools = get_all_tools()
    
    results = []
    for tool in all_tools:
        if query:
            if query in tool.name.lower() or query in tool.description.lower():
                results.append(tool)
        else:
            results.append(tool)
    
    if category:
        results = [t for t in results if t.risk_level == category]
    
    if not results:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="No tools found matching your query",
            is_error=False,
        )
    
    lines = []
    for tool in results:
        lines.append(f"- {tool.name}: {tool.description} (risk: {tool.risk_level})")
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output="\n".join(lines),
        is_error=False,
    )


TOOL_SEARCH_TOOL = ToolDef(
    name="tool_search",
    description="Search for available tools by name or description.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "category": {"type": "string", "enum": ["low", "medium", "high"], "description": "Filter by risk level"},
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=_tool_search,
)


__all__ = ["TOOL_SEARCH_TOOL"]
