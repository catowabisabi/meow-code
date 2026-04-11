"""Tool orchestration service for coordinating tool execution."""
import asyncio
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional

from .execution import ExecutionResult, ToolExecutor
from .hooks import ToolHooks, get_max_tool_use_concurrency


@dataclass
class Batch:
    is_concurrency_safe: bool
    blocks: list[dict[str, Any]]


@dataclass
class MessageUpdate:
    message: Optional[Any] = None
    new_context: Optional[Any] = None


class ToolOrchestration:
    
    def __init__(
        self,
        tools: list[Any],
        hooks: Optional[ToolHooks] = None,
        max_concurrency: Optional[int] = None,
    ) -> None:
        self._tools = tools
        self._hooks = hooks or ToolHooks()
        self._max_concurrency = max_concurrency or get_max_tool_use_concurrency()
        self._executor = ToolExecutor(tools)
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: Any,
    ) -> ExecutionResult:
        pre_hook_results = await self._hooks.run_pre_tool_hooks(
            tool_name=tool_name,
            tool_use_id=getattr(context, "tool_use_id", ""),
            tool_input=tool_input,
            context=context,
        )
        
        for result in pre_hook_results:
            if result.get("blocking_error") or result.get("prevent_continuation"):
                return ExecutionResult(
                    success=False,
                    error=result.get("blocking_error") or result.get("stop_reason") or "Hook prevented execution",
                )
        
        execution_result = await self._executor.execute(
            tool_name=tool_name,
            tool_input=tool_input,
            context=context,
        )
        
        post_hook_results = await self._hooks.run_post_tool_hooks(
            tool_name=tool_name,
            tool_use_id=getattr(context, "tool_use_id", ""),
            tool_input=tool_input,
            tool_output=execution_result.data,
            context=context,
        )
        
        for result in post_hook_results:
            if result.get("updated_mcp_tool_output"):
                execution_result.data = result.get("updated_mcp_tool_output")
        
        return execution_result
    
    async def execute_tools(
        self,
        tool_requests: list[dict[str, Any]],
        assistant_messages: list[dict[str, Any]],
        context: Any,
    ) -> AsyncGenerator[MessageUpdate, None]:
        batches = self._partition_tool_calls(tool_requests, context)
        
        current_context = context
        for batch in batches:
            if batch.is_concurrency_safe:
                async for update in self._run_tools_concurrently(
                    batch.blocks,
                    assistant_messages,
                    current_context,
                ):
                    if update.message:
                        yield update
                    if update.new_context:
                        current_context = update.new_context
            else:
                async for update in self._run_tools_serially(
                    batch.blocks,
                    assistant_messages,
                    current_context,
                ):
                    if update.message:
                        yield update
                    if update.new_context:
                        current_context = update.new_context
    
    def validate_tool_request(self, tool_request: dict[str, Any]) -> tuple[bool, Optional[str]]:
        tool_name = tool_request.get("name")
        tool_input = tool_request.get("input", {})
        
        if not tool_name:
            return False, "Tool name is required"
        
        tool = self._find_tool(tool_name)
        if not tool:
            return False, f"No such tool available: {tool_name}"
        
        input_schema = getattr(tool, "input_schema", None)
        if input_schema:
            safe_parse = getattr(input_schema, "safe_parse", None)
            if safe_parse:
                result = safe_parse(tool_input)
                if hasattr(result, "success") and not result.success:
                    return False, f"Input validation failed: {result.error}"
        
        return True, None
    
    def get_tool_schema(self, tool_name: str) -> Optional[dict[str, Any]]:
        tool = self._find_tool(tool_name)
        if not tool:
            return None
        
        input_schema = getattr(tool, "input_schema", None)
        if input_schema and hasattr(input_schema, "schema"):
            return input_schema.schema()
        
        return getattr(tool, "input_schema", None)
    
    def _find_tool(self, tool_name: str) -> Optional[Any]:
        for tool in self._tools:
            if getattr(tool, "name", None) == tool_name:
                return tool
        return None
    
    def _partition_tool_calls(
        self,
        tool_use_messages: list[dict[str, Any]],
        context: Any,
    ) -> list[Batch]:
        batches: list[Batch] = []
        
        for tool_use in tool_use_messages:
            tool_name = tool_use.get("name", "")
            tool = self._find_tool(tool_name)
            
            is_concurrency_safe = False
            if tool:
                parsed_input = self._safe_parse_input(tool, tool_use.get("input", {}))
                if parsed_input:
                    try:
                        is_concurrency_safe_fn = getattr(tool, "is_concurrency_safe", None)
                        if is_concurrency_safe_fn:
                            is_concurrency_safe = bool(is_concurrency_safe_fn(parsed_input))
                    except Exception:
                        is_concurrency_safe = False
            
            if is_concurrency_safe and batches and batches[-1].is_concurrency_safe:
                batches[-1].blocks.append(tool_use)
            else:
                batches.append(Batch(
                    is_concurrency_safe=is_concurrency_safe,
                    blocks=[tool_use],
                ))
        
        return batches
    
    def _safe_parse_input(self, tool: Any, tool_input: dict[str, Any]) -> Optional[dict[str, Any]]:
        input_schema = getattr(tool, "input_schema", None)
        if input_schema is None:
            return tool_input
        
        safe_parse = getattr(input_schema, "safe_parse", None)
        if safe_parse is None:
            return tool_input
        
        result = safe_parse(tool_input)
        if hasattr(result, "success") and result.success:
            return getattr(result, "data", tool_input)
        return None
    
    async def _run_tools_serially(
        self,
        tool_use_messages: list[dict[str, Any]],
        assistant_messages: list[dict[str, Any]],
        context: Any,
    ) -> AsyncGenerator[MessageUpdate, None]:
        current_context = context
        
        for tool_use in tool_use_messages:
            tool_use_id = tool_use.get("id", "")
            
            if hasattr(current_context, "set_in_progress_tool_use_ids"):
                current_context.set_in_progress_tool_use_ids(
                    lambda prev, uid=tool_use_id: prev | {uid}
                )
            
            assistant_msg = self._find_assistant_message(assistant_messages, tool_use_id)
            
            try:
                async for update in self._execute_single_tool(
                    tool_use,
                    assistant_msg,
                    current_context,
                ):
                    yield update
                    if update.new_context:
                        current_context = update.new_context
            finally:
                if hasattr(current_context, "set_in_progress_tool_use_ids"):
                    current_context.set_in_progress_tool_use_ids(
                        lambda prev, uid=tool_use_id: prev - {uid}
                    )
    
    async def _run_tools_concurrently(
        self,
        tool_use_messages: list[dict[str, Any]],
        assistant_messages: list[dict[str, Any]],
        context: Any,
    ) -> AsyncGenerator[MessageUpdate, None]:
        tasks = []
        
        for tool_use in tool_use_messages:
            tool_use_id = tool_use.get("id", "")
            assistant_msg = self._find_assistant_message(assistant_messages, tool_use_id)
            
            if hasattr(context, "set_in_progress_tool_use_ids"):
                context.set_in_progress_tool_use_ids(
                    lambda prev, uid=tool_use_id: prev | {uid}
                )
            
            tasks.append(self._execute_single_tool(tool_use, assistant_msg, context))
        
        for coro in asyncio.as_completed(tasks, timeout=self._max_concurrency):
            try:
                async for update in await coro:
                    yield update
            except Exception:
                pass
    
    async def _execute_single_tool(
        self,
        tool_use: dict[str, Any],
        assistant_message: Optional[dict[str, Any]],
        context: Any,
    ) -> AsyncGenerator[MessageUpdate, None]:
        tool_name = tool_use.get("name", "")
        tool_input = tool_use.get("input", {})
        tool_use_id = tool_use.get("id", "")
        
        pre_hook_results = await self._hooks.run_pre_tool_hooks(
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            tool_input=tool_input,
            context=context,
        )
        
        for result in pre_hook_results:
            if result.get("message"):
                yield MessageUpdate(message=result.get("message"), new_context=context)
            
            if result.get("blocking_error") or result.get("prevent_continuation"):
                yield MessageUpdate(
                    message=self._create_error_message(
                        tool_use_id,
                        result.get("blocking_error") or result.get("stop_reason") or "Hook prevented execution",
                    ),
                    new_context=context,
                )
                return
        
        result = await self._executor.execute(
            tool_name=tool_name,
            tool_input=tool_input,
            context=context,
        )
        
        post_hook_results = await self._hooks.run_post_tool_hooks(
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            tool_input=tool_input,
            tool_output=result.data,
            context=context,
        )
        
        for hook_result in post_hook_results:
            if hook_result.get("message"):
                yield MessageUpdate(message=hook_result.get("message"), new_context=context)
        
        yield MessageUpdate(
            message=self._create_result_message(tool_use_id, result),
            new_context=context,
        )
    
    def _find_assistant_message(
        self,
        assistant_messages: list[dict[str, Any]],
        tool_use_id: str,
    ) -> Optional[dict[str, Any]]:
        for msg in assistant_messages:
            content = msg.get("message", {}).get("content", [])
            for block in content:
                if block.get("type") == "tool_use" and block.get("id") == tool_use_id:
                    return msg
        return None
    
    def _create_error_message(self, tool_use_id: str, error: str) -> dict[str, Any]:
        return {
            "type": "user",
            "message": {
                "content": [{
                    "type": "tool_result",
                    "content": f"<tool_use_error>{error}</tool_use_error>",
                    "is_error": True,
                    "tool_use_id": tool_use_id,
                }],
            },
        }
    
    def _create_result_message(self, tool_use_id: str, result: ExecutionResult) -> dict[str, Any]:
        return {
            "type": "user",
            "message": {
                "content": [{
                    "type": "tool_result",
                    "content": result.data if result.data else result.error or "",
                    "is_error": result.error is not None,
                    "tool_use_id": tool_use_id,
                }],
                "tool_use_result": result.data or result.error,
            },
        }
