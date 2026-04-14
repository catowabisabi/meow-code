"""
WebSocket chat handler — FULL AGENTIC LOOP.

The core loop:
  1. User sends message
  2. AI responds (possibly with tool_calls)
  3. If tool_calls → execute each tool → collect results
  4. Feed tool results back to AI as new messages
  5. AI responds again (possibly with more tool_calls)
  6. Repeat until AI gives final text (no tool_calls), or max iterations

This is what makes the agent autonomous — it can plan, execute,
verify, and self-correct in a continuous loop.
"""

import asyncio
import json
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncGenerator
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

from .protocol import (
    ClientMessage,
    ServerMessage,
    ServerStreamStart,
    ServerStreamDelta,
    ServerStreamEnd,
    ServerToolUseStart,
    ServerToolResult,
    ServerError,
    ServerSessionInfo,
    ServerModelSwitched,
    ServerPong,
    ContentBlock,
    UnifiedMessage,
    ToolCall,
    ToolCallResult,
)
from api_server.tools import execute_tool, ToolContext
from api_server.tools.types import ToolCall as ToolCallDataclass
from api_server.adapters.router import AdapterRouter
from api_server.adapters.anthropic import AnthropicAdapter
from api_server.adapters.openai import OpenAIAdapter
from api_server.adapters.minimax import MiniMaxAdapter
from api_server.adapters.deepseek import DeepSeekAdapter
from api_server.models.message import Message
from api_server.models.tool import ToolDefinition

MAX_AGENT_ITERATIONS = 25


def _get_provider_config(provider: str) -> dict:
    """Load full config (api_key, base_url) for a provider."""
    config = {"api_key": "", "base_url": ""}
    try:
        from api_server.db.settings_db import get_api_credential
        cred = get_api_credential(provider)
        if cred:
            if cred.get("api_key"):
                config["api_key"] = cred["api_key"]
            if cred.get("base_url"):
                config["base_url"] = cred["base_url"]
            if config["api_key"]:
                return config
    except Exception:
        pass
    try:
        import json as _json
        from pathlib import Path
        config_path = Path.home() / ".claude" / "models.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            providers = data.get("providers", {})
            if provider in providers:
                pc = providers[provider]
                if isinstance(pc, dict):
                    config["api_key"] = pc.get("apiKey") or pc.get("api_key") or ""
                    config["base_url"] = pc.get("baseUrl") or pc.get("base_url") or ""
    except Exception:
        pass
    return config


def _get_api_key_for_provider(provider: str) -> str:
    """Load API key for a provider from settings database or models.json."""
    try:
        from api_server.db.settings_db import get_api_credential
        cred = get_api_credential(provider)
        if cred and cred.get("api_key"):
            return cred["api_key"]
    except Exception:
        pass
    
    try:
        import json
        from pathlib import Path
        config_path = Path.home() / ".claude" / "models.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            providers = config.get("providers", {})
            if provider in providers:
                provider_config = providers[provider]
                if isinstance(provider_config, dict):
                    api_key = provider_config.get("apiKey") or provider_config.get("api_key") or provider_config.get("api-key")
                    if api_key:
                        return api_key
                elif isinstance(provider_config, str):
                    return provider_config
            if provider in config:
                provider_config = config[provider]
                if isinstance(provider_config, dict):
                    api_key = provider_config.get("apiKey") or provider_config.get("api_key") or provider_config.get("api-key")
                    if api_key:
                        return api_key
    except Exception:
        pass
    
    return ""


def _get_adapter_router() -> AdapterRouter:
    """Get or create the global adapter router."""
    from api_server.adapters import router as router_module

    if hasattr(router_module, 'adapter_router'):
        return router_module.adapter_router

    router = AdapterRouter()
    _, default_provider = _load_default_model_config()

    adapter_classes = {
        "anthropic": AnthropicAdapter,
        "openai": OpenAIAdapter,
        "minimax": MiniMaxAdapter,
        "deepseek": DeepSeekAdapter,
    }

    for provider_name, adapter_cls in adapter_classes.items():
        try:
            pc = _get_provider_config(provider_name)
            if not pc["api_key"]:
                continue
            kwargs = {"api_key": pc["api_key"]}
            if pc["base_url"]:
                kwargs["base_url"] = pc["base_url"]
            adapter = adapter_cls(**kwargs)
            is_default = (provider_name == default_provider)
            router.register_adapter(provider_name, adapter, set_default=is_default)
        except Exception:
            pass

    router_module.adapter_router = router
    return router


class StreamEventType(str, Enum):
    STREAM_START = "stream_start"
    STREAM_TEXT_DELTA = "stream_text_delta"
    STREAM_THINKING_DELTA = "stream_thinking_delta"
    STREAM_TOOL_USE_START = "stream_tool_use_start"
    STREAM_TOOL_USE_DELTA = "stream_tool_use_delta"
    STREAM_TOOL_USE_END = "stream_tool_use_end"
    STREAM_END = "stream_end"
    STREAM_ERROR = "stream_error"


@dataclass
class ChatSession:
    id: str
    model: str
    provider: str
    mode: str
    folder: Optional[str]
    title: str
    messages: List[UnifiedMessage]
    created_at: int
    abort_controller: Optional["asyncio.Event"] = None
    pending_permissions: Dict[str, asyncio.Future] = field(default_factory=dict)
    iteration_count: int = 0


# ─── Session Management ────────────────────────────────────────

sessions: Dict[str, ChatSession] = {}


def get_session(session_id: str) -> Optional[ChatSession]:
    return sessions.get(session_id)


def get_all_sessions() -> List[ChatSession]:
    return sorted(sessions.values(), key=lambda s: s.created_at, reverse=True)


def _load_default_model_config() -> tuple[str, str]:
    """Load default model and provider from config."""
    try:
        import json
        from pathlib import Path
        
        config_path = Path.home() / ".claude" / "models.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            default_model = config.get("defaultModel", "claude-sonnet-4-20250514")
            default_provider = config.get("defaultProvider", "anthropic")
            return default_model, default_provider
    except Exception:
        pass
    return "claude-sonnet-4-20250514", "anthropic"


def create_session(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    mode: Optional[str] = None,
    folder: Optional[str] = None,
) -> ChatSession:
    default_model, default_provider = _load_default_model_config()

    session = ChatSession(
        id=str(uuid.uuid4()),
        model=model or default_model,
        provider=provider or default_provider,
        mode=mode or "chat",
        folder=folder,
        title="",
        messages=[],
        created_at=int(time.time() * 1000),
        abort_controller=None,
        pending_permissions={},
        iteration_count=0,
    )
    sessions[session.id] = session
    return session


def _persist_session(session: ChatSession) -> None:
    """Save a chat session to disk so it survives server restarts."""
    from pathlib import Path as _Path

    sessions_dir = _Path.home() / ".claude" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = sessions_dir / f"{session.id}.json"

    messages = session.messages
    # Generate a short title from the first user message
    title = session.title or ""
    if not title:
        for m in messages:
            if m.get("role") == "user":
                content = m.get("content", "")
                if isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "text":
                            content = b.get("text", "")
                            break
                    else:
                        content = ""
                if isinstance(content, str) and content:
                    title = content[:50] + ("..." if len(content) > 50 else "")
                    break
        if not title:
            title = "New Chat"

    data = {
        "id": session.id,
        "title": title,
        "mode": session.mode,
        "folder": session.folder,
        "model": session.model,
        "provider": session.provider,
        "messages": messages,
        "createdAt": datetime.utcfromtimestamp(session.created_at / 1000).isoformat()
        if isinstance(session.created_at, (int, float))
        else str(session.created_at),
        "updatedAt": datetime.utcnow().isoformat(),
    }

    import json as _json

    with open(path, "w", encoding="utf-8") as f:
        _json.dump(data, f, ensure_ascii=False, indent=2, default=str)


# ─── WebSocket Handler ────────────────────────────────────────


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket connection handler."""
    await websocket.accept()
    
    session: Optional[ChatSession] = None
    
    try:
        while True:
            data = await websocket.receive_text()
            msg: ClientMessage = json.loads(data)
            
            msg_type = msg.get("type")
            
            if msg_type == "ping":
                await send_message(websocket, ServerPong(type="pong"))
                continue
            
            elif msg_type == "user_message":
                session = await handle_user_message(websocket, msg, session)
            
            elif msg_type == "abort":
                if session and session.abort_controller:
                    session.abort_controller.set()
                continue
            
            elif msg_type == "switch_model":
                if session:
                    session.model = msg.get("model", session.model)
                    session.provider = msg.get("provider", session.provider)
                    await send_message(websocket, ServerModelSwitched(
                        type="model_switched",
                        model=session.model,
                        provider=session.provider,
                    ))
                continue
            
            elif msg_type == "permission_response":
                if session:
                    tool_use_id = msg.get("toolUseId")
                    allowed = msg.get("allowed", False)
                    if tool_use_id in session.pending_permissions:
                        future = session.pending_permissions.pop(tool_use_id)
                        future.set_result(allowed)
                continue
    
    except WebSocketDisconnect:
        pass
    finally:
        if session and session.abort_controller:
            session.abort_controller.set()


async def handle_user_message(
    websocket: WebSocket,
    msg: ClientMessage,
    existing_session: Optional[ChatSession],
) -> Optional[ChatSession]:
    """Handle incoming user message and start agentic loop."""
    session = existing_session
    
    # If client sends sessionId, try to use existing session
    if msg.get("sessionId") and not session:
        session = sessions.get(msg["sessionId"])
    
    if not session:
        session = create_session(
            model=msg.get("model"),
            provider=msg.get("provider"),
            mode=msg.get("mode"),
            folder=msg.get("folder"),
        )
        await send_message(websocket, ServerSessionInfo(
            type="session_info",
            sessionId=session.id,
            model=session.model,
            provider=session.provider,
        ))
    
    # Update model/provider if provided
    if msg.get("model"):
        session.model = msg["model"]
    if msg.get("provider"):
        session.provider = msg["provider"]
    
    content_blocks: List[ContentBlock] = [{"type": "text", "text": msg["content"]}]
    
    attachments = msg.get("attachments")
    if attachments:
        for att in attachments:
            if att.get("type") == "image":
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": att.get("mimeType"),
                        "data": att.get("data"),
                    },
                })
    
    session.messages.append({"role": "user", "content": content_blocks})
    session.iteration_count = 0
    await agentic_loop(websocket, session)

    # Auto-save session to disk after each exchange
    _persist_session(session)

    return session


async def agentic_loop(websocket: WebSocket, session: ChatSession) -> None:
    """Main agentic loop implementation."""
    abort_event = asyncio.Event()
    session.abort_controller = abort_event

    # Track repeated tool calls to prevent infinite retries
    MAX_SAME_TOOL_RETRIES = 3
    MAX_SAME_TYPE_CALLS = 4  # max times the same tool NAME can be called total
    tool_call_counts: Dict[str, int] = {}  # "tool_name:key_arg" -> count
    tool_type_counts: Dict[str, int] = {}  # "tool_name" -> total count

    try:
        while session.iteration_count < MAX_AGENT_ITERATIONS:
            if abort_event.is_set():
                break

            session.iteration_count += 1
            result = await stream_and_collect(websocket, session, abort_event)

            if abort_event.is_set():
                break

            if result["assistant_blocks"]:
                session.messages.append({
                    "role": "assistant",
                    "content": result["assistant_blocks"],
                })

            if not result["tool_calls"] or result["stop_reason"] != "tool_use":
                await send_message(websocket, ServerStreamEnd(
                    type="stream_end",
                    stopReason="end_turn",
                ))
                break

            # Check for repeated tool calls (same args OR same tool type too many times)
            has_exceeded = False
            exceeded_tool = ""
            for tc in result["tool_calls"]:
                name = tc.get("name", "")
                inp = tc.get("input", {}) or tc.get("arguments", {})
                key_arg = str(inp.get("query") or inp.get("command") or inp.get("url") or inp.get("path") or "")
                sig = f"{name}:{key_arg}"
                tool_call_counts[sig] = tool_call_counts.get(sig, 0) + 1
                tool_type_counts[name] = tool_type_counts.get(name, 0) + 1
                if tool_call_counts[sig] > MAX_SAME_TOOL_RETRIES:
                    has_exceeded = True
                    exceeded_tool = name
                if tool_type_counts[name] > MAX_SAME_TYPE_CALLS:
                    has_exceeded = True
                    exceeded_tool = name

            if has_exceeded:
                # Inject an error message so AI knows to stop retrying
                err_block: ContentBlock = {
                    "type": "tool_result",
                    "tool_use_id": result["tool_calls"][-1].get("id", ""),
                    "content": f"⚠️ Tool '{exceeded_tool}' has been called too many times. "
                               f"STOP calling this tool. Use the information you already have to answer the user's question. "
                               f"If you cannot answer, tell the user what went wrong.",
                    "is_error": True,
                }
                session.messages.append({"role": "user", "content": [err_block]})
                continue

            await send_message(websocket, ServerStreamDelta(
                type="stream_delta",
                contentType="text",
                text="",
            ))

            tool_results = await execute_tool_calls_mock(
                tool_calls=result["tool_calls"],
                session=session,
                websocket=websocket,
                abort_event=abort_event,
            )

            if abort_event.is_set():
                break

            # Match Claude Code's limits: 50K per result, 200K per message aggregate
            MAX_SINGLE_RESULT_CHARS = 50_000
            MAX_AGGREGATE_CHARS = 200_000
            PREVIEW_SIZE = 2000

            tool_result_blocks: List[ContentBlock] = []
            aggregate_size = 0
            for r in tool_results:
                output = r["output"]
                output_len = len(output)

                # If single result exceeds 50K or would push aggregate past 200K,
                # replace with a preview (like Claude Code's persist-to-disk strategy)
                if output_len > MAX_SINGLE_RESULT_CHARS or (aggregate_size + output_len) > MAX_AGGREGATE_CHARS:
                    preview = output[:PREVIEW_SIZE]
                    last_nl = preview.rfind('\n', int(PREVIEW_SIZE * 0.5))
                    if last_nl > 0:
                        preview = preview[:last_nl]
                    output = (
                        f"<large-output>\n"
                        f"Output too large ({output_len:,} chars). Preview (first ~2KB):\n"
                        f"{preview}\n...\n"
                        f"</large-output>"
                    )

                aggregate_size += len(output)
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": r["tool_call_id"],
                    "content": output,
                    "is_error": r["isError"],
                })

            session.messages.append({"role": "user", "content": tool_result_blocks})
        
        if session.iteration_count >= MAX_AGENT_ITERATIONS:
            await send_message(websocket, ServerError(
                type="error",
                message=f"Agent loop reached maximum iterations ({MAX_AGENT_ITERATIONS}). Stopping to prevent infinite loops.",
            ))
    
    except Exception as e:
        logger.exception("Agentic loop error: %s", e)
        if not abort_event.is_set():
            await send_message(websocket, ServerError(
                type="error",
                message=str(e),
            ))
            # Always send stream_end so frontend exits streaming state
            await send_message(websocket, ServerStreamEnd(
                type="stream_end",
                stopReason="error",
            ))
    finally:
        session.abort_controller = None


async def stream_and_collect(
    websocket: WebSocket,
    session: ChatSession,
    abort_event: asyncio.Event,
) -> Dict[str, Any]:
    """Stream AI response and collect tool calls."""
    assistant_blocks: List[ContentBlock] = []
    tool_calls: List[ToolCall] = []
    current_text = ""
    current_thinking = ""
    stop_reason = "end_turn"
    
    pending_tool_calls: Dict[str, Dict[str, str]] = {}
    
    is_first = session.iteration_count == 1
    
    if is_first:
        await send_message(websocket, ServerStreamStart(
            type="stream_start",
            messageId=str(uuid.uuid4()),
            sessionId=session.id,
            model=session.model,
            provider=session.provider,
        ))
    
    # Real AI streaming response via adapter router
    async for event in stream_ai_response(
        session=session,
        abort_event=abort_event,
    ):
        if abort_event.is_set():
            break
        
        event_type = event.get("type")
        
        if event_type == StreamEventType.STREAM_TEXT_DELTA:
            current_text += event["text"]
            await send_message(websocket, ServerStreamDelta(
                type="stream_delta",
                contentType="text",
                text=event["text"],
            ))
        
        elif event_type == StreamEventType.STREAM_THINKING_DELTA:
            current_thinking += event["text"]
            await send_message(websocket, ServerStreamDelta(
                type="stream_delta",
                contentType="thinking",
                text=event["text"],
            ))
        
        elif event_type == StreamEventType.STREAM_TOOL_USE_START:
            pending_tool_calls[event["toolId"]] = {
                "name": event["toolName"],
                "inputJson": "",
            }
        
        elif event_type == StreamEventType.STREAM_TOOL_USE_DELTA:
            pending = pending_tool_calls.get(event["toolId"])
            if pending:
                pending["inputJson"] += event["inputDelta"]
        
        elif event_type == StreamEventType.STREAM_TOOL_USE_END:
            # Finalize accumulated text
            if current_text:
                assistant_blocks.append({"type": "text", "text": current_text})
                current_text = ""
            if current_thinking:
                assistant_blocks.append({"type": "thinking", "text": current_thinking})
                current_thinking = ""
            
            tool_name = pending_tool_calls.get(event["toolId"], {}).get("name", "")
            
            assistant_blocks.append({
                "type": "tool_use",
                "id": event["toolId"],
                "name": tool_name,
                "input": event["input"],
            })
            
            tool_calls.append({
                "id": event["toolId"],
                "name": tool_name,
                "arguments": event["input"],
            })
            
            pending_tool_calls.pop(event["toolId"], None)
        
        elif event_type == StreamEventType.STREAM_END:
            if current_text:
                assistant_blocks.append({"type": "text", "text": current_text})
            if current_thinking:
                assistant_blocks.append({"type": "thinking", "text": current_thinking})
            stop_reason = event.get("stopReason", "end_turn")
        
        elif event_type == StreamEventType.STREAM_ERROR:
            logger.error("Stream error from AI: %s", event.get("error"))
            await send_message(websocket, ServerError(
                type="error",
                message=event["error"],
            ))
            # On error, finalize whatever text we have and stop
            if current_text:
                assistant_blocks.append({"type": "text", "text": current_text})
                current_text = ""
            if current_thinking:
                assistant_blocks.append({"type": "thinking", "text": current_thinking})
                current_thinking = ""
            stop_reason = "error"
            break

    return {
        "assistant_blocks": assistant_blocks,
        "tool_calls": tool_calls if stop_reason != "error" else [],  # Don't execute tools on error
        "stop_reason": stop_reason,
    }


# ─── Real AI Streaming ────────────────────────────────────────


def _convert_session_messages_to_adapter_messages(
    session: ChatSession,
) -> List[Message]:
    """Convert session messages to adapter Message format."""
    result = []
    
    for msg in session.messages:
        role = msg.get("role", "user")
        content_blocks = msg.get("content", [])
        
        if isinstance(content_blocks, str):
            content_blocks = [{"type": "text", "text": content_blocks}]
        
        result.append(Message(role=role, content=content_blocks))
    
    return result


def _build_system_prompt(session: ChatSession) -> str:
    """Build system prompt that enforces tool usage."""
    cwd = session.folder or "."
    return f"""You are Cato, an autonomous AI coding assistant. You have access to tools and MUST use them.

## CRITICAL RULES
1. Every response to a task MUST use tools. NEVER just describe what you would do — DO IT.
2. NEVER answer questions about code or files without reading them first using tools.
3. NEVER speculate about file contents, directory structures, or system state. Use tools to check.
4. When asked to search, list, read, edit, or run anything — execute the appropriate tool immediately.
5. If you need multiple pieces of information, call multiple tools.

## AVAILABLE ACTIONS
- Read/write/edit files: use file_read, file_write, file_edit
- Search files: use glob, grep
- Run commands: use Bash (for shell commands on any platform)
- Web: use web_fetch, web_search

## ENVIRONMENT
- Working directory: {cwd}
- Platform: Windows
- Shell: PowerShell / CMD

## RESPONSE FORMAT
- Act first, explain after. Lead with tool calls, then summarize results.
- If a task requires multiple steps, execute them sequentially using tools.
- Only respond with plain text when no tool action is needed (e.g., answering a general knowledge question).

## TOOL USAGE LIMITS
- After calling web_search and getting results, ANSWER IMMEDIATELY using those results. Do NOT search again unless the results are completely irrelevant.
- Do NOT call the same tool more than 2-3 times. If results are unsatisfactory, answer with what you have and explain the limitation.
- If a tool returns an error, try ONE alternative approach. If that also fails, inform the user.
- NEVER fetch a URL just to "verify" search results — the search snippets are sufficient for answering."""


async def stream_ai_response(
    session: ChatSession,
    abort_event: asyncio.Event,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Real AI streaming response using the adapter router.
    """
    router = _get_adapter_router()
    
    message_id = str(uuid.uuid4())
    
    yield {
        "type": StreamEventType.STREAM_START,
        "messageId": message_id,
    }
    
    adapter_messages = _convert_session_messages_to_adapter_messages(session)
    
    if not adapter_messages:
        yield {
            "type": StreamEventType.STREAM_ERROR,
            "error": "No messages in session",
        }
        return
    
    from api_server.tools import get_tool_schemas_for_anthropic
    tools = get_tool_schemas_for_anthropic()
    tool_defs = [
        ToolDefinition(
            name=t["name"],
            description=t.get("description", ""),
            input_schema=t.get("input_schema", {}),
        )
        for t in tools
    ]
    
    try:
        async for event in router.route_chat(
            provider=session.provider or "anthropic",
            messages=adapter_messages,
            model=session.model or "claude-sonnet-4-20250514",
            system_prompt=_build_system_prompt(session),
            tools=tool_defs,
            stream=True,
        ):
            if abort_event.is_set():
                break
            
            if event.type == "stream_start":
                continue
            
            elif event.type == "stream_text_delta":
                yield {
                    "type": StreamEventType.STREAM_TEXT_DELTA,
                    "text": event.text or "",
                }
            
            elif event.type == "stream_thinking_delta":
                yield {
                    "type": StreamEventType.STREAM_THINKING_DELTA,
                    "text": event.text or "",
                }
            
            elif event.type == "stream_tool_use_start":
                yield {
                    "type": StreamEventType.STREAM_TOOL_USE_START,
                    "toolId": event.tool_id or str(uuid.uuid4()),
                    "toolName": event.tool_name or "",
                }
            
            elif event.type == "stream_tool_use_delta":
                yield {
                    "type": StreamEventType.STREAM_TOOL_USE_DELTA,
                    "toolId": event.tool_id or "",
                    "inputDelta": event.tool_input_delta or "",
                }
            
            elif event.type == "stream_tool_use_end":
                yield {
                    "type": StreamEventType.STREAM_TOOL_USE_END,
                    "toolId": event.tool_id or "",
                    "toolName": event.tool_name or "",
                    "input": event.tool_input or {},
                }
            
            elif event.type == "stream_end":
                yield {
                    "type": StreamEventType.STREAM_END,
                    "stopReason": event.stop_reason or "end_turn",
                }
            
            elif event.type == "stream_error":
                yield {
                    "type": StreamEventType.STREAM_ERROR,
                    "error": event.error or "Unknown error",
                }
    
    except Exception as e:
        logger.exception("AI streaming error: %s", e)
        yield {
            "type": StreamEventType.STREAM_ERROR,
            "error": str(e),
        }
        # Ensure stream_end is always emitted so the loop knows to stop
        yield {
            "type": StreamEventType.STREAM_END,
            "stopReason": "error",
        }


# ─── Mock Tool Executor ────────────────────────────────────────


async def execute_tool_calls_real(
    tool_calls: List[ToolCall],
    session: ChatSession,
    websocket: WebSocket,
    abort_event: asyncio.Event,
) -> List[ToolCallResult]:
    """Real tool executor using api_server.tools."""
    results: List[ToolCallResult] = []
    
    def abort_signal() -> bool:
        return abort_event.is_set()
    
    ctx = ToolContext(
        cwd=".",
        abort_signal=abort_signal,
        request_permission=None,
        on_progress=None,
    )
    
    for tool_call in tool_calls:
        if abort_event.is_set():
            break

        tool_id = tool_call["id"]
        tool_name = tool_call["name"]
        tool_args = tool_call.get("arguments") or tool_call.get("input") or {}

        await send_message(websocket, ServerToolUseStart(
            type="tool_use_start",
            toolId=tool_id,
            toolName=tool_name,
            input=tool_args,
        ))

        try:
            result = await execute_tool(
                ToolCallDataclass(id=tool_id, name=tool_name, arguments=tool_args),
                ctx,
            )
            output = result.output
            is_error = result.is_error
        except Exception as e:
            logger.exception("Tool execution error (%s): %s", tool_name, e)
            output = f"Tool execution failed: {str(e)}"
            is_error = True

        await send_message(websocket, ServerToolResult(
            type="tool_result",
            toolId=tool_id,
            toolName=tool_name,
            output=output[:5000],
            isError=is_error,
        ))

        results.append({
            "tool_call_id": tool_id,
            "output": output,
            "isError": is_error,
        })
    
    return results


async def execute_tool_calls_mock(
    tool_calls: List[ToolCall],
    session: ChatSession,
    websocket: WebSocket,
    abort_event: asyncio.Event,
) -> List[ToolCallResult]:
    """Mock tool executor for testing - falls back to real if available."""
    return await execute_tool_calls_real(tool_calls, session, websocket, abort_event)


# ─── Permission Request Helper ─────────────────────────────────


async def request_permission_mock(
    session: ChatSession,
    tool_name: str,
    tool_input: dict,
    description: str,
) -> bool:
    """
    Request permission from user (mock implementation).
    
    In real implementation, this would send a permission_request
    and wait for user response.
    """
    perm_id = str(uuid.uuid4())
    future: asyncio.Future = asyncio.get_event_loop().create_future()
    session.pending_permissions[perm_id] = future
    
    await asyncio.sleep(0.1)
    future.set_result(True)
    
    return future.result()


# ─── Utility Functions ──────────────────────────────────────────


async def send_message(websocket: WebSocket, msg: ServerMessage) -> None:
    try:
        await websocket.send_json(msg)
    except Exception:
        pass
