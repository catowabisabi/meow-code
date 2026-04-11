"""
Async generator for full agent loop with MCP server initialization,
skill preloading, hook registration, and transcript recording.
"""
import asyncio
import json
import secrets
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Optional

from ...adapters.router import AdapterRouter
from ...adapters.anthropic import AnthropicAdapter
from ...adapters.openai import OpenAIAdapter
from ...models.message import Message
from ...models.tool import ToolDefinition
from ...tools.types import ToolContext as BaseToolContext
from .mcp import initialize_agent_mcp_servers
from .types import AgentDefinition, AgentResult, AgentSpawnParams


def create_agent_id() -> str:
    """Create a unique agent ID."""
    alphabet = "012345abcdefghijklmnopqrstuvwxyz"
    suffix = "".join(alphabet[secrets.randbelow(len(alphabet))] for _ in range(8))
    return f"a{suffix}"


@dataclass
class AgentMessage:
    """Message in agent conversation."""
    type: str
    content: Any
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class TranscriptRecord:
    """Transcript record for persistence."""
    messages: list[AgentMessage]
    agent_id: str
    agent_type: str


_agent_transcripts: dict[str, list[AgentMessage]] = {}
_agent_metadata: dict[str, dict] = {}
_session_hooks: dict[str, list[Any]] = {}


async def _record_transcript(
    messages: list[AgentMessage],
    agent_id: str,
    parent_uuid: Optional[str] = None,
) -> None:
    """Record messages to transcript storage."""
    if agent_id not in _agent_transcripts:
        _agent_transcripts[agent_id] = []
    _agent_transcripts[agent_id].extend(messages)


async def _write_agent_metadata(
    agent_id: str,
    metadata: dict,
) -> None:
    """Write agent metadata to storage."""
    _agent_metadata[agent_id] = metadata


async def _clear_session_hooks(
    agent_id: str,
) -> None:
    """Clear session hooks for agent."""
    if agent_id in _session_hooks:
        del _session_hooks[agent_id]


async def _register_frontmatter_hooks(
    agent_id: str,
    hooks: list[Any],
    agent_type: str,
) -> None:
    """Register hooks from agent frontmatter."""
    _session_hooks[agent_id] = list(hooks)


async def _execute_subagent_start_hooks(
    agent_id: str,
    agent_type: str,
    signal: asyncio.AbstractServer,
) -> list[str]:
    """Execute SubagentStart hooks and collect additional context."""
    hooks = _session_hooks.get(agent_id, [])
    contexts = []
    for hook in hooks:
        if hasattr(hook, 'get_context'):
            try:
                ctx = hook.get_context(agent_type)
                if ctx:
                    contexts.append(ctx)
            except Exception:
                pass
    return contexts


async def _get_skill_prompts(
    skill_names: list[str],
) -> dict[str, str]:
    """Get skill prompts by name."""
    return {}


async def _filter_incomplete_tool_calls(
    messages: list[AgentMessage],
) -> list[AgentMessage]:
    """Filter out assistant messages with incomplete tool calls."""
    tool_use_ids_with_results = set()
    
    for message in messages:
        if message.type == 'user':
            content = message.content
            if isinstance(content, list):
                for block in content:
                    if block.get('type') == 'tool_result' and block.get('tool_use_id'):
                        tool_use_ids_with_results.add(block['tool_use_id'])
    
    def has_incomplete_tool_call(msg: AgentMessage) -> bool:
        if msg.type != 'assistant':
            return False
        content = msg.content
        if isinstance(content, list):
            return any(
                block.get('type') == 'tool_use' and
                block.get('id') and
                block.get('id') not in tool_use_ids_with_results
                for block in content
            )
        return False
    
    return [m for m in messages if not has_incomplete_tool_call(m)]


async def _create_subagent_context(
    parent_context: BaseToolContext,
    options: dict[str, Any],
) -> BaseToolContext:
    """Create subagent context from parent context."""
    return parent_context


async def _resolve_agent_tools(
    agent_definition: AgentDefinition,
    available_tools: list[Any],
    is_async: bool,
) -> list[Any]:
    """Resolve tools for agent based on definition."""
    return available_tools


async def _get_agent_system_prompt(
    agent_definition: AgentDefinition,
    tool_use_context: BaseToolContext,
    resolved_agent_model: str,
    additional_working_directories: list[str],
    resolved_tools: list[Any],
) -> str:
    """Get system prompt for agent."""
    return agent_definition.prompt_template or ""


async def _merge_mcp_tools(
    resolved_tools: list[Any],
    agent_mcp_tools: list[Any],
) -> list[Any]:
    """Merge agent MCP tools with resolved tools, deduplicating by name."""
    seen = set()
    result = []
    for tool in resolved_tools + agent_mcp_tools:
        if hasattr(tool, 'name') and tool.name not in seen:
            seen.add(tool.name)
            result.append(tool)
    return result


async def run_agent(
    agent_definition: AgentDefinition,
    prompt_messages: list[AgentMessage],
    tool_use_context: BaseToolContext,
    can_use_tool: Callable[[str], bool],
    is_async: bool,
    max_turns: Optional[int] = None,
    fork_context_messages: Optional[list[AgentMessage]] = None,
    allowed_tools: Optional[list[str]] = None,
    worktree_path: Optional[str] = None,
    description: Optional[str] = None,
    transcript_subdir: Optional[str] = None,
    on_query_progress: Optional[Callable[[], None]] = None,
) -> AsyncGenerator[AgentMessage, None]:
    """
    Async generator for full agent loop.
    
    Args:
        agent_definition: Agent definition with type, tools, etc.
        prompt_messages: Initial prompt messages
        tool_use_context: Tool execution context
        can_use_tool: Function to check if tool can be used
        is_async: Whether agent runs asynchronously
        max_turns: Maximum turns (defaults to agent definition or 100)
        fork_context_messages: Messages from parent for forked agents
        allowed_tools: Tool permission rules
        worktree_path: Worktree path for isolated agents
        description: Task description
        transcript_subdir: Subdirectory for transcript grouping
        on_query_progress: Callback for query progress
    
    Yields:
        AgentMessage objects from the agent loop
    """
    agent_id = create_agent_id()
    
    resolved_tools = await _resolve_agent_tools(
        agent_definition, 
        tool_use_context.options.get('tools', []) if hasattr(tool_use_context, 'options') else [],
        is_async
    )
    
    mcp_clients = tool_use_context.options.get('mcpClients', []) if hasattr(tool_use_context, 'options') else []
    merged_mcp_clients, agent_mcp_tools, mcp_cleanup = await initialize_agent_mcp_servers(
        agent_definition,
        mcp_clients,
    )
    
    all_tools = await _merge_mcp_tools(resolved_tools, agent_mcp_tools)
    
    initial_messages = list(prompt_messages)
    if fork_context_messages:
        filtered = await _filter_incomplete_tool_calls(fork_context_messages)
        initial_messages = filtered + initial_messages
    
    hooks_allowed = True
    if agent_definition.hooks and hooks_allowed:
        await _register_frontmatter_hooks(
            agent_id,
            agent_definition.hooks,
            agent_definition.agent_type,
        )
    
    additional_contexts: list[str] = []
    abort_controller = asyncio.AbortController() if is_async else None
    
    for ctx in await _execute_subagent_start_hooks(
        agent_id,
        agent_definition.agent_type,
        abort_controller.signal if abort_controller else asyncio.get_event_loop(),
    ):
        if ctx:
            additional_contexts.append(ctx)
    
    if additional_contexts:
        hook_message = AgentMessage(
            type='user',
            content=[{'type': 'text', 'text': ctx} for ctx in additional_contexts],
        )
        initial_messages.insert(0, hook_message)
    
    agent_options = {
        'isNonInteractiveSession': is_async,
        'tools': all_tools,
        'mainLoopModel': agent_definition.model,
        'mcpClients': merged_mcp_clients,
    }
    
    agent_tool_use_context = await _create_subagent_context(
        tool_use_context,
        agent_options,
    )
    
    await _record_transcript(initial_messages, agent_id)
    await _write_agent_metadata(agent_id, {
        'agentType': agent_definition.agent_type,
        'worktreePath': worktree_path,
        'description': description,
    })
    
    last_recorded_uuid: Optional[str] = initial_messages[-1].uuid if initial_messages else None
    
    try:
        async for message in _query_loop(
            initial_messages=initial_messages,
            agent_definition=agent_definition,
            tool_use_context=agent_tool_use_context,
            can_use_tool=can_use_tool,
            max_turns=max_turns or agent_definition.max_turns or 100,
        ):
            on_query_progress()
            
            if message.type in ('assistant', 'user', 'progress', 'system'):
                await _record_transcript([message], agent_id, last_recorded_uuid)
                if message.type != 'progress':
                    last_recorded_uuid = message.uuid
            
            yield message
            
            if abort_controller and abort_controller.aborted:
                break
    
    finally:
        await mcp_cleanup()
        
        if agent_definition.hooks:
            await _clear_session_hooks(agent_id)
        
        if hasattr(tool_use_context, 'readFileState'):
            tool_use_context.readFileState.clear()


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
    from ...adapters import router as router_module
    
    if hasattr(router_module, 'adapter_router'):
        return router_module.adapter_router
    
    router = AdapterRouter()
    
    try:
        anthropic_api_key = _get_api_key_for_provider("anthropic")
        anthropic_adapter = AnthropicAdapter(api_key=anthropic_api_key)
        router.register_adapter("anthropic", anthropic_adapter, set_default=True)
    except Exception:
        pass
    
    try:
        openai_api_key = _get_api_key_for_provider("openai")
        openai_adapter = OpenAIAdapter(api_key=openai_api_key)
        router.register_adapter("openai", openai_adapter)
    except Exception:
        pass
    
    router_module.adapter_router = router
    return router


def _convert_agent_messages_to_messages(
    agent_messages: list[AgentMessage],
) -> list[Message]:
    """Convert AgentMessage list to Message list for adapter."""
    result = []
    
    for msg in agent_messages:
        content = msg.content
        
        if isinstance(content, dict) and 'content' in content:
            content_blocks = content['content']
        elif isinstance(content, list):
            content_blocks = content
        else:
            content_blocks = [{'type': 'text', 'text': str(content)}]
        
        role = 'user' if msg.type in ('user', 'progress') else 'assistant'
        
        result.append(Message(role=role, content=content_blocks))
    
    return result


def _convert_tool_schemas(tools: list[Any]) -> list[ToolDefinition]:
    """Convert tool definitions for adapter."""
    result = []
    
    for tool in tools:
        if isinstance(tool, ToolDefinition):
            result.append(tool)
        elif hasattr(tool, 'name') and hasattr(tool, 'description') and hasattr(tool, 'input_schema'):
            result.append(ToolDefinition(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
            ))
        elif isinstance(tool, dict):
            result.append(ToolDefinition(
                name=tool.get('name', ''),
                description=tool.get('description', ''),
                input_schema=tool.get('input_schema', {}),
            ))
    
    return result


async def _query_loop(
    initial_messages: list[AgentMessage],
    agent_definition: AgentDefinition,
    tool_use_context: BaseToolContext,
    can_use_tool: Callable[[str], bool],
    max_turns: int,
) -> AsyncGenerator[AgentMessage, None]:
    """
    Core query loop for agent execution.
    
    Connects to the AdapterRouter to get LLM responses with streaming support.
    Handles text deltas, thinking deltas, and tool use events.
    """
    router = _get_adapter_router()
    
    messages_history = list(initial_messages)
    turn = 0
    accumulated_content: list[dict] = []
    current_text = ""
    current_thinking = ""
    pending_tool_use: dict[str, dict] = {}
    
    def create_abort_signal() -> Optional[asyncio.Event]:
        if hasattr(tool_use_context, 'abort_signal'):
            abort_fn = tool_use_context.abort_signal
            if callable(abort_fn) and isinstance(abort_fn(), asyncio.Event):
                return abort_fn()
        return None
    
    abort_event = create_abort_signal()
    
    while turn < max_turns:
        turn += 1
        
        if abort_event and abort_event.is_set():
            break
        
        adapter_messages = _convert_agent_messages_to_messages(messages_history)
        
        tools = []
        if hasattr(tool_use_context, 'options') and tool_use_context.options:
            tools = tool_use_context.options.get('tools', [])
        
        tool_defs = _convert_tool_schemas(tools) if tools else []
        
        provider = tool_use_context.options.get('provider', 'anthropic') if hasattr(tool_use_context, 'options') else 'anthropic'
        model = agent_definition.model or 'claude-sonnet-4-20250514'
        
        try:
            async for event in router.route_chat(
                provider=provider,
                messages=adapter_messages,
                model=model,
                system_prompt="",
                tools=tool_defs,
                stream=True,
            ):
                if abort_event and abort_event.is_set():
                    break
                
                if event.type == "stream_start":
                    continue
                
                elif event.type == "stream_text_delta":
                    current_text += event.text or ""
                    yield AgentMessage(
                        type='assistant',
                        content={
                            'content': [{'type': 'text', 'text': event.text or ""}]
                        },
                    )
                
                elif event.type == "stream_thinking_delta":
                    current_thinking += event.text or ""
                    yield AgentMessage(
                        type='progress',
                        content={
                            'content': [{'type': 'thinking', 'text': event.text or ""}]
                        },
                    )
                
                elif event.type == "stream_tool_use_start":
                    pending_tool_use[event.tool_id] = {
                        'id': event.tool_id,
                        'name': event.tool_name,
                        'input_json': "",
                    }
                
                elif event.type == "stream_tool_use_delta":
                    if event.tool_id in pending_tool_use:
                        pending_tool_use[event.tool_id]['input_json'] += event.tool_input_delta or ""
                
                elif event.type == "stream_tool_use_end":
                    if event.tool_id in pending_tool_use:
                        tool_info = pending_tool_use.pop(event.tool_id)
                        try:
                            tool_input = json.loads(tool_info['input_json']) if tool_info['input_json'] else {}
                        except json.JSONDecodeError:
                            tool_input = {'__raw': tool_info['input_json']}
                        
                        accumulated_content.append({
                            'type': 'tool_use',
                            'id': event.tool_id,
                            'name': event.tool_name,
                            'input': event.tool_input or tool_input,
                        })
                
                elif event.type == "stream_end":
                    if current_text:
                        accumulated_content.append({'type': 'text', 'text': current_text})
                        current_text = ""
                    if current_thinking:
                        accumulated_content.append({'type': 'thinking', 'text': current_thinking})
                        current_thinking = ""
                    
                    if pending_tool_use:
                        for tool_id, tool_info in pending_tool_use.items():
                            try:
                                tool_input = json.loads(tool_info['input_json']) if tool_info['input_json'] else {}
                            except json.JSONDecodeError:
                                tool_input = {'__raw': tool_info['input_json']}
                            
                            accumulated_content.append({
                                'type': 'tool_use',
                                'id': tool_id,
                                'name': tool_info['name'],
                                'input': tool_input,
                            })
                        pending_tool_use.clear()
                    
                    if accumulated_content:
                        yield AgentMessage(
                            type='assistant',
                            content={'content': accumulated_content},
                        )
                        accumulated_content = []
                    
                    return
                
                elif event.type == "stream_error":
                    yield AgentMessage(
                        type='system',
                        content={'content': [{'type': 'text', 'text': f"Error: {event.error}"}]},
                    )
                    return
            
            if abort_event and abort_event.is_set():
                break
        
        except Exception as e:
            yield AgentMessage(
                type='system',
                content={'content': [{'type': 'text', 'text': f"Exception: {str(e)}"}]},
            )
            return
        
        if abort_event and abort_event.is_set():
            break


async def run_agent_loop(
    agent_id: str,
    params: AgentSpawnParams,
    tool_context: BaseToolContext,
) -> AgentResult:
    """
    Run agent loop and return result.
    
    This function bridges the async generator pattern with the existing
    spawn-based execution model.
    """
    agent_definition = AgentDefinition(
        name=params.name,
        agent_type=params.agent_type,
        model=params.model,
        prompt_template=params.prompt,
        tools=params.tools or [],
        max_turns=params.max_turns,
        mcp_servers=[],
    )
    
    prompt_messages = [
        AgentMessage(type='user', content={'content': [{'type': 'text', 'text': params.prompt}]})
    ]
    
    messages: list[AgentMessage] = []
    output_parts: list[str] = []
    
    async def can_use_tool(tool_name: str) -> bool:
        return True
    
    try:
        async for message in run_agent(
            agent_definition=agent_definition,
            prompt_messages=prompt_messages,
            tool_use_context=tool_context,
            can_use_tool=can_use_tool,
            is_async=True,
            max_turns=params.max_turns,
            worktree_path=params.worktree_path,
            description=params.description,
        ):
            messages.append(message)
            
            if message.type == 'assistant':
                content = message.content
                if isinstance(content, dict) and 'content' in content:
                    for block in content['content']:
                        if block.get('type') == 'text':
                            output_parts.append(block.get('text', ''))
        
        return AgentResult(
            success=True,
            agent_id=agent_id,
            output=''.join(output_parts),
            messages=[m.content for m in messages],
        )
    
    except Exception as e:
        return AgentResult(
            success=False,
            agent_id=agent_id,
            output='',
            error=str(e),
            messages=[m.content for m in messages],
        )
