"""Tool execution logic for async tool execution."""
import asyncio
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Optional


@dataclass
class ExecutionResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    tool_use_id: str = ""


@dataclass
class StreamProgress:
    tool_use_id: str
    data: Any


class AbortController:
    def __init__(self) -> None:
        self._signal = asyncio.Event()
        self._reason: Optional[str] = None
    
    @property
    def signal(self) -> asyncio.Event:
        return self._signal
    
    @property
    def aborted(self) -> bool:
        return self._signal.is_set()
    
    @property
    def reason(self) -> Optional[str]:
        return self._reason
    
    def abort(self, reason: str = "") -> None:
        self._reason = reason
        self._signal.set()
    
    def add_event_listener(self, event: str, handler: Callable) -> None:
        if event == "abort":
            self._signal.add_done_callback(handler)


class ToolExecutor:
    
    def __init__(
        self,
        tools: list[Any],
        timeout_ms: Optional[int] = None,
    ) -> None:
        self._tools = tools
        self._timeout_ms = timeout_ms
        self._abort_controller = AbortController()
    
    async def execute(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: Any,
    ) -> ExecutionResult:
        tool = self._find_tool(tool_name)
        if not tool:
            return ExecutionResult(
                success=False,
                error=f"No such tool available: {tool_name}",
            )
        
        try:
            parsed_input = self._validate_input(tool, tool_input)
            if parsed_input is None:
                return ExecutionResult(
                    success=False,
                    error=f"Input validation failed for {tool_name}",
                )
            
            is_valid = await self._validate_call(tool, parsed_input, context)
            if not is_valid:
                return ExecutionResult(
                    success=False,
                    error=f"Tool validation failed for {tool_name}",
                )
            
            result = await self._execute_with_timeout(
                tool,
                parsed_input,
                context,
            )
            
            return ExecutionResult(
                success=True,
                data=result,
                tool_use_id=getattr(context, "tool_use_id", ""),
            )
        
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                error=f"Tool execution timed out after {self._timeout_ms}ms",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Error calling tool {tool_name}: {str(e)}",
            )
    
    async def stream_output(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: Any,
        on_progress: Callable[[StreamProgress], None],
    ) -> AsyncGenerator[dict[str, Any], None]:
        tool = self._find_tool(tool_name)
        if not tool:
            yield {
                "type": "error",
                "error": f"No such tool available: {tool_name}",
            }
            return
        
        try:
            parsed_input = self._validate_input(tool, tool_input)
            if parsed_input is None:
                yield {
                    "type": "error",
                    "error": f"Input validation failed for {tool_name}",
                }
                return
            
            is_valid = await self._validate_call(tool, parsed_input, context)
            if not is_valid:
                yield {
                    "type": "error",
                    "error": f"Tool validation failed for {tool_name}",
                }
                return
            
            async for chunk in self._stream_execute(tool, parsed_input, context):
                if isinstance(chunk, dict) and chunk.get("type") == "progress":
                    on_progress(StreamProgress(
                        tool_use_id=chunk.get("tool_use_id", ""),
                        data=chunk.get("data"),
                    ))
                yield chunk
        
        except asyncio.TimeoutError:
            yield {
                "type": "error",
                "error": f"Tool execution timed out after {self._timeout_ms}ms",
            }
        except Exception as e:
            yield {
                "type": "error",
                "error": f"Error calling tool {tool_name}: {str(e)}",
            }
    
    def handle_timeout(self, tool_name: str) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "content": f"<tool_use_error>Tool execution timed out after {self._timeout_ms}ms</tool_use_error>",
            "is_error": True,
            "tool_use_id": "",
        }
    
    def _find_tool(self, tool_name: str) -> Optional[Any]:
        for tool in self._tools:
            if getattr(tool, "name", None) == tool_name:
                return tool
        return None
    
    def _validate_input(self, tool: Any, tool_input: dict[str, Any]) -> Optional[dict[str, Any]]:
        input_schema = getattr(tool, "input_schema", None)
        if input_schema is None:
            return tool_input
        
        safe_parse = getattr(input_schema, "safe_parse", None)
        if safe_parse is None:
            return tool_input
        
        result = safe_parse(tool_input)
        if hasattr(result, "success"):
            if result.success:
                return getattr(result, "data", tool_input)
            return None
        
        return tool_input
    
    async def _validate_call(
        self,
        tool: Any,
        parsed_input: dict[str, Any],
        context: Any,
    ) -> bool:
        validate_input = getattr(tool, "validate_input", None)
        if validate_input is None:
            return True
        
        if asyncio.iscoroutinefunction(validate_input):
            result = await validate_input(parsed_input, context)
        else:
            result = validate_input(parsed_input, context)
        
        if isinstance(result, dict):
            return result.get("result", True)
        if isinstance(result, bool):
            return result
        return True
    
    async def _execute_with_timeout(
        self,
        tool: Any,
        parsed_input: dict[str, Any],
        context: Any,
    ) -> Any:
        tool_call = getattr(tool, "call", None)
        if tool_call is None:
            raise ValueError(f"Tool {getattr(tool, 'name', 'unknown')} has no call method")
        
        if self._timeout_ms:
            return await asyncio.wait_for(
                tool_call(parsed_input, context),
                timeout=self._timeout_ms / 1000.0,
            )
        
        if asyncio.iscoroutinefunction(tool_call):
            return await tool_call(parsed_input, context)
        return tool_call(parsed_input, context)
    
    async def _stream_execute(
        self,
        tool: Any,
        parsed_input: dict[str, Any],
        context: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        tool_call = getattr(tool, "call", None)
        if tool_call is None:
            raise ValueError("Tool has no call method")
        
        result_gen = tool_call(parsed_input, context)
        if asyncio.iscoroutine(result_gen):
            result = await result_gen
            if hasattr(result, "__iter__"):
                for item in result:
                    yield item
        elif hasattr(result, "__aiter__"):
            async for item in result:
                yield item
        else:
            yield {"type": "result", "data": result}
