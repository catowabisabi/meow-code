import asyncio
import contextvars
from dataclasses import dataclass, field
from typing import Callable, AsyncIterator

from ..adapters.base import BaseAdapter
from ..tools.executor import execute_tool_calls
from ..tools.types import ToolCall, ToolContext, ToolCallResult
from ..models.message import Message
from .task.types import TaskType, generate_task_id


class AgentEvent(str):
    TEXT_DELTA = "text_delta"
    THINKING_DELTA = "thinking_delta"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    STREAM_END = "stream_end"
    ERROR = "error"


@dataclass
class TextDeltaEvent:
    type: str = "text_delta"
    text: str = ""


@dataclass
class ThinkingDeltaEvent:
    type: str = "thinking_delta"
    thinking: str = ""


@dataclass
class ToolUseEvent:
    type: str = "tool_use"
    tool_name: str = ""
    tool_input: dict = field(default_factory=dict)
    tool_id: str = ""


@dataclass
class ToolResultEvent:
    type: str = "tool_result"
    tool_id: str = ""
    tool_name: str = ""
    result: ToolCallResult | None = None


@dataclass
class StreamEndEvent:
    type: str = "stream_end"


@dataclass
class ErrorEvent:
    type: str = "error"
    message: str = ""
    is_error: bool = True


AgentEventType = TextDeltaEvent | ThinkingDeltaEvent | ToolUseEvent | ToolResultEvent | StreamEndEvent | ErrorEvent


@dataclass
class AgentContext:
    session_id: str
    model: str
    adapter: BaseAdapter
    cwd: str = "/"
    abort_signal: asyncio.Event | None = None
    on_progress: Callable[[dict], None] | None = None


_agent_context: contextvars.ContextVar[AgentContext | None] = contextvars.ContextVar("_agent_context", default=None)


def get_current_agent_context() -> AgentContext | None:
    return _agent_context.get()


def run_with_agent_context(ctx: AgentContext, coro):
    token = _agent_context.set(ctx)
    try:
        return coro
    finally:
        _agent_context.reset(token)


async def run_agent_loop(
    session_id: str,
    messages: list[Message],
    adapter: BaseAdapter,
    tools: list[dict],
    model: str,
    cwd: str = "/",
    abort_signal: asyncio.Event | None = None,
    on_progress: Callable[[dict], None] | None = None,
    max_iterations: int = 100,
) -> AsyncIterator[AgentEventType]:
    tool_calls_batch: list[ToolCall] = []
    text_buffer = ""
    iteration = 0
    
    tool_context = ToolContext(
        cwd=cwd,
        abort_signal=abort_signal,
        request_permission=None,
        on_progress=on_progress,
    )
    
    while iteration < max_iterations:
        iteration += 1
        tool_calls_batch.clear()
        text_buffer = ""
        
        if abort_signal and abort_signal.is_set():
            yield ErrorEvent(message="User aborted", is_error=True)
            break
        
        async for event in adapter.chat(messages, tools):
            if event.type == "text_delta":
                text_buffer += event.text
                yield TextDeltaEvent(text=event.text)
                
            elif event.type == "thinking_delta":
                yield ThinkingDeltaEvent(thinking=event.thinking)
                
            elif event.type == "tool_use_start":
                tc = ToolCall(
                    id=event.tool_id or f"tc_{iteration}",
                    name=event.tool_name,
                    arguments=event.tool_input or {},
                )
                tool_calls_batch.append(tc)
                yield ToolUseEvent(
                    tool_name=event.tool_name,
                    tool_input=event.tool_input or {},
                    tool_id=tc.id,
                )
                
            elif event.type == "tool_use_delta":
                if tool_calls_batch and event.tool_name == tool_calls_batch[-1].name:
                    existing_args = tool_calls_batch[-1].arguments
                    if isinstance(event.tool_input, dict):
                        existing_args.update(event.tool_input)
                    else:
                        existing_args["__raw__"] = str(event.tool_input)
                        
            elif event.type == "tool_use_end":
                pass
                
            elif event.type == "stream_end":
                pass
                
            elif event.type == "error":
                yield ErrorEvent(message=event.message, is_error=True)
        
        if not tool_calls_batch:
            yield StreamEndEvent()
            break
        
        results = await execute_tool_calls(tool_calls_batch, tool_context)
        
        for i, result in enumerate(results):
            yield ToolResultEvent(
                tool_id=tool_calls_batch[i].id,
                tool_name=tool_calls_batch[i].name,
                result=result,
            )
            
            content_block = {
                "type": "tool_result",
                "tool_use_id": tool_calls_batch[i].id,
                "content": result.output,
            }
            messages.append(Message(role="user", content=[content_block]))
        
        if abort_signal and abort_signal.is_set():
            yield ErrorEvent(message="User aborted", is_error=True)
            break
    
    if iteration >= max_iterations:
        yield ErrorEvent(message=f"Max iterations ({max_iterations}) reached", is_error=True)


async def run_agent_simple(
    messages: list[Message],
    adapter: BaseAdapter,
    tools: list[dict],
    model: str,
    system_prompt: str | None = None,
) -> tuple[str, list[ToolCallResult]]:
    if system_prompt:
        messages = [Message(role="system", content=system_prompt)] + messages
    
    all_text = []
    all_tool_results: list[ToolCallResult] = []
    
    async for event in run_agent_loop(
        session_id="simple",
        messages=messages,
        adapter=adapter,
        tools=tools,
        model=model,
    ):
        if isinstance(event, TextDeltaEvent):
            all_text.append(event.text)
        elif isinstance(event, ToolResultEvent) and event.result:
            all_tool_results.append(event.result)
        elif isinstance(event, ErrorEvent):
            all_text.append(f"[Error: {event.message}]")
    
    return "".join(all_text), all_tool_results
