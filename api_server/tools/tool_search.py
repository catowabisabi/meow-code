"""
ToolSearchTool - Search for available tools by name or description.

Provides keyword-based search over deferred tools with:
- Name matching
- Description search
- MCP tool support
- Result scoring and ranking

Based on the TypeScript ToolSearchTool implementation in _claude_code_leaked_source_code.
"""
import json
import re
from typing import Any

from .types import ToolDef, ToolContext, ToolResult
from .executor import get_all_tools


TOOL_NAME = "ToolSearch"


def _parse_tool_name(name: str) -> tuple[list[str], str, bool]:
    if name.startswith("mcp__"):
        without_prefix = name[5:].lower()
        parts = without_prefix.split("__")
        flat_parts = []
        for p in parts:
            flat_parts.extend(p.split("_"))
        parts = [x for x in flat_parts if x]
        return parts, without_prefix.replace("__", " "), True
    
    parts = name
    parts = re.sub(r"([a-z])([A-Z])", r"\1 \2", parts)
    parts = parts.replace("_", " ")
    parts = parts.lower()
    split_parts = [x for x in parts.split() if x]
    return split_parts, " ".join(split_parts), False


def _compile_term_patterns(terms: list[str]) -> dict[str, Any]:
    patterns = {}
    for term in terms:
        if term not in patterns:
            patterns[term] = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
    return patterns


async def _tool_search(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    query = args.get("query", "")
    max_results = args.get("max_results", 5)
    
    all_tools = get_all_tools()
    
    if not query:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: query is required",
            is_error=True,
        )
    
    if query.startswith("select:"):
        selected = query[7:].split(",")
        selected = [s.strip() for s in selected if s.strip()]
        
        found = []
        missing = []
        for tool_name in selected:
            tool = next((t for t in all_tools if t.name.lower() == tool_name.lower()), None)
            if tool:
                found.append(tool.name)
            else:
                missing.append(tool_name)
        
        if not found:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=json.dumps({
                    "matches": [],
                    "query": query,
                    "total_deferred_tools": len(all_tools),
                    "message": f"None found: {', '.join(missing)}" if missing else "No matches",
                }),
                is_error=False,
            )
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "matches": found,
                "query": query,
                "total_deferred_tools": len(all_tools),
            }),
            is_error=False,
        )
    
    query_lower = query.lower().strip()
    query_terms = query_lower.split()
    
    term_patterns = _compile_term_patterns(query_terms)
    
    scored = []
    for tool in all_tools:
        parsed_name, full_name, is_mcp = _parse_tool_name(tool.name)
        desc_lower = tool.description.lower()
        hint_lower = getattr(tool, "search_hint", "").lower()
        
        score = 0
        for term, pattern in term_patterns.items():
            if term in parsed_name:
                score += 12 if is_mcp else 10
            elif any(term in p for p in parsed_name):
                score += 6 if is_mcp else 5
            elif full_name.startswith(term):
                score += 3
            elif pattern.search(desc_lower):
                score += 2
            elif hint_lower and pattern.search(hint_lower):
                score += 4
        
        if score > 0:
            scored.append((tool.name, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    matches = [name for name, _ in scored[:max_results]]
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=json.dumps({
            "matches": matches,
            "query": query,
            "total_deferred_tools": len(all_tools),
        }),
        is_error=False,
    )


TOOL_SEARCH_TOOL = ToolDef(
    name=TOOL_NAME,
    description="Search for deferred tools by name or description. Use 'select:<tool_name>' for direct selection.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Query to find deferred tools. Use 'select:<tool_name>' for direct selection, or keywords to search.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5)",
            },
        },
        "required": ["query"],
    },
    is_read_only=True,
    risk_level="low",
    execute=_tool_search,
)


__all__ = ["TOOL_SEARCH_TOOL"]
