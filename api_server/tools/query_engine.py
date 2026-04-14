"""QueryEngine - bridging gap with TypeScript QueryEngine.ts"""
import asyncio
import logging
from typing import Callable, Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import json


logger = logging.getLogger(__name__)


class QueryEngineState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ToolExecution:
    tool_name: str
    tool_input: Dict[str, Any]
    tool_call_id: str
    result: Optional[Any] = None
    error: Optional[str] = None
    is_streaming: bool = False


@dataclass
class QueryResult:
    message: str
    tool_results: List[ToolExecution]
    is_complete: bool
    error: Optional[str] = None


@dataclass
class StreamEvent:
    type: str
    data: Any


class ToolExecutor:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
    
    def register(self, name: str, handler: Callable) -> None:
        self._tools[name] = handler
    
    async def execute(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        handler = self._tools[tool_name]
        
        if asyncio.iscoroutinefunction(handler):
            return await handler(tool_input, context)
        else:
            return handler(tool_input, context)


class QueryEngine:
    """
    Central coordinator for headless/SDK mode.
    
    TypeScript equivalent: QueryEngine.ts
    Python gap: Simple loop.py lacks streaming, reactive compact, media recovery.
    """
    
    def __init__(self):
        self.state = QueryEngineState.IDLE
        self._tool_executor = ToolExecutor()
        self._streaming_handlers: List[Callable] = []
        self._compact_enabled = True
        self._max_turns = 100
        self._current_turn = 0
    
    def register_tool(self, name: str, handler: Callable) -> None:
        self._tool_executor.register(name, handler)
    
    def register_streaming_handler(self, handler: Callable) -> None:
        self._streaming_handlers.append(handler)
    
    async def execute_query(
        self,
        prompt: str,
        tools: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        self.state = QueryEngineState.RUNNING
        self._current_turn = 0
        
        tool_results: List[ToolExecution] = []
        messages: List[str] = []
        
        try:
            while self._current_turn < self._max_turns:
                self._current_turn += 1
                
                message, should_stream = await self._generate_message(prompt, tools, context)
                messages.append(message)
                
                for handler in self._streaming_handlers:
                    await handler(StreamEvent(type="message", data=message))
                
                tool_calls = self._extract_tool_calls(message)
                
                if not tool_calls:
                    break
                
                for tool_call in tool_calls:
                    result = await self._execute_tool_call(tool_call, context)
                    tool_results.append(result)
                    
                    for handler in self._streaming_handlers:
                        await handler(StreamEvent(type="tool_result", data=result))
                
                if self._should_compact(messages, tool_results):
                    messages = await self._compact_messages(messages, tool_results)
                    for handler in self._streaming_handlers:
                        await handler(StreamEvent(type="compact", data={"message_count": len(messages)}))
            
            self.state = QueryEngineState.COMPLETED
            
            return QueryResult(
                message="\n".join(messages),
                tool_results=tool_results,
                is_complete=True
            )
            
        except Exception as e:
            self.state = QueryEngineState.ERROR
            return QueryResult(
                message="",
                tool_results=tool_results,
                is_complete=False,
                error=str(e)
            )
    
    async def _generate_message(
        self,
        prompt: str,
        tools: List[str],
        context: Optional[Dict[str, Any]]
    ) -> tuple[str, bool]:
        return f"[Turn {self._current_turn}] {prompt}", False
    
    def _extract_tool_calls(self, message: str) -> List[Dict[str, Any]]:
        tool_calls = []
        
        try:
            if message.strip().startswith("["):
                data = json.loads(message)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "tool" in item:
                            tool_calls.append(item)
        except json.JSONDecodeError:
            pass
        
        return tool_calls
    
    async def _execute_tool_call(
        self,
        tool_call: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> ToolExecution:
        tool_name = tool_call.get("tool", "unknown")
        tool_input = tool_call.get("input", {})
        tool_call_id = tool_call.get("id", "")
        
        try:
            result = await self._tool_executor.execute(
                tool_name,
                tool_input,
                context or {}
            )
            return ToolExecution(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_call_id=tool_call_id,
                result=result
            )
        except Exception as e:
            return ToolExecution(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_call_id=tool_call_id,
                error=str(e)
            )
    
    def _should_compact(self, messages: List[str], tool_results: List[ToolExecution]) -> bool:
        if not self._compact_enabled:
            return False
        
        total_content = sum(len(m) for m in messages)
        total_tool_results = len(tool_results)
        
        return total_content > 50000 or total_tool_results > 50
    
    async def _compact_messages(
        self,
        messages: List[str],
        tool_results: List[ToolExecution]
    ) -> List[str]:
        summary = f"[Compacted {len(messages)} messages, {len(tool_results)} tool results]"
        return [summary]
    
    def set_state(self, state: QueryEngineState) -> None:
        self.state = state
    
    def pause(self) -> None:
        if self.state == QueryEngineState.RUNNING:
            self.state = QueryEngineState.PAUSED
    
    def resume(self) -> None:
        if self.state == QueryEngineState.PAUSED:
            self.state = QueryEngineState.RUNNING
    
    def get_state(self) -> QueryEngineState:
        return self.state


_query_engine: Optional[QueryEngine] = None


def get_query_engine() -> QueryEngine:
    global _query_engine
    if _query_engine is None:
        _query_engine = QueryEngine()
    return _query_engine
