"""Tool Executor Engine - manages tool registration, concurrent execution, and orchestration."""
import asyncio
from typing import Dict, List, Optional, Callable, Awaitable

from .types import (
    ToolDef,
    ToolContext,
    ToolCall,
    ToolCallResult,
    ToolProgress,
    ToolEvent,
    ToolStartEvent,
    ToolProgressEvent,
    ToolEndEvent,
)


tool_registry: Dict[str, ToolDef] = {}


def register_tool(tool: ToolDef) -> None:
    """Register a tool in the global registry."""
    tool_registry[tool.name] = tool


def get_tool(name: str) -> Optional[ToolDef]:
    """Get a tool definition by name."""
    return tool_registry.get(name)


def get_all_tools() -> List[ToolDef]:
    """Get all registered tools."""
    return list(tool_registry.values())


def get_tool_schemas_for_ai() -> List[Dict]:
    """Get all tool definitions in OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            },
        }
        for t in get_all_tools()
    ]


def get_tool_schemas_for_anthropic() -> List[Dict]:
    """Get all tool definitions in Anthropic format."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in get_all_tools()
    ]


async def execute_tool(
    tool_call: ToolCall,
    ctx: ToolContext,
    on_event: Optional[Callable[[ToolEvent], Awaitable[None]]] = None,
) -> ToolCallResult:
    """Execute a single tool call with permission checking and event emission."""
    tool = get_tool(tool_call.name)

    if not tool:
        return ToolCallResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            output=f"Unknown tool: {tool_call.name}. Available tools: {', '.join(t.name for t in get_all_tools())}",
            is_error=True,
        )

    if not hasattr(tool, 'execute') or tool.execute is None:
        return ToolCallResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            output=f"Tool '{tool_call.name}' is registered but has no execute handler.",
            is_error=True,
        )

    if on_event:
        await on_event(
            ToolStartEvent(
                tool_id=tool_call.id,
                tool_name=tool_call.name,
                input=tool_call.arguments,
            )
        )

    risk_level = getattr(tool, 'risk_level', 'low')
    if risk_level == "high" and ctx.request_permission:
        desc = f"Execute {tool.name}: {str(tool_call.arguments)[:200]}"
        allowed = await ctx.request_permission(tool.name, tool_call.arguments, desc)
        if not allowed:
            result = ToolCallResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                output="Permission denied by user.",
                is_error=True,
            )
            if on_event:
                await on_event(ToolEndEvent(tool_id=tool_call.id, tool_name=tool_call.name, result=result))
            return result

    try:
        async def progress_wrapper(progress: ToolProgress) -> None:
            progress.tool_id = tool_call.id
            await on_event(ToolProgressEvent(tool_id=tool_call.id, tool_name=tool_call.name, progress=progress)) if on_event else None

        tool_result = await tool.execute(tool_call.arguments, ToolContext(
            cwd=ctx.cwd,
            abort_signal=ctx.abort_signal,
            request_permission=ctx.request_permission,
            on_progress=progress_wrapper,
        ))

        result = ToolCallResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            output=tool_result.output,
            is_error=tool_result.is_error,
        )

        await on_event(ToolEndEvent(tool_id=tool_call.id, tool_name=tool_call.name, result=result)) if on_event else None
        return result

    except Exception as err:
        err_msg = str(err)
        result = ToolCallResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            output=f"Tool execution error: {err_msg}",
            is_error=True,
        )
        await on_event(ToolEndEvent(tool_id=tool_call.id, tool_name=tool_call.name, result=result)) if on_event else None
        return result


async def execute_tool_calls(
    tool_calls: List[ToolCall],
    ctx: ToolContext,
    on_event: Optional[Callable[[ToolEvent], Awaitable[None]]] = None,
) -> List[ToolCallResult]:
    """
    Execute multiple tool calls with smart concurrency:
    - Read-only tools run in parallel (max concurrency: 10)
    - Write tools run one at a time, serially
    """
    MAX_CONCURRENT = 10

    read_calls: List[ToolCall] = []
    write_calls: List[ToolCall] = []

    for tc in tool_calls:
        tool = get_tool(tc.name)
        if tool and tool.is_read_only:
            read_calls.append(tc)
        else:
            write_calls.append(tc)

    results: List[ToolCallResult] = []

    for i in range(0, len(read_calls), MAX_CONCURRENT):
        batch = read_calls[i : i + MAX_CONCURRENT]
        batch_results = await asyncio.gather(*[execute_tool(tc, ctx, on_event) for tc in batch])
        results.extend(batch_results)

    for tc in write_calls:
        result = await execute_tool(tc, ctx, on_event)
        results.append(result)

    return results