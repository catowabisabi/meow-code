"""
Execute agent tool operations: spawn, run, resume, fork, status, send_message, terminate, list.
"""
from ...tools.types import ToolContext
from .memory import (
    AgentMemoryScope,
    create_agent_memory,
    get_agent_memory,
)
from .registry import (
    get_agent,
    list_agents,
    register_agent,
    set_agent_output,
    set_agent_status,
    unregister_agent,
)
from .run_agent import run_agent, AgentMessage
from .spawn import spawn_agent
from .types import AgentDefinition, AgentSpawnParams


async def execute_agent_tool(
    operation: str,
    args: dict,
    ctx: ToolContext,
) -> dict:
    if operation == "spawn":
        params = AgentSpawnParams(
            name=args.get("name", ""),
            agent_type=args.get("agent_type", "general"),
            model=args.get("model"),
            prompt=args.get("prompt", ""),
            tools=args.get("tools"),
            max_turns=args.get("max_turns"),
            cwd=args.get("cwd", "/"),
            worktree_path=args.get("worktree_path"),
            description=args.get("description"),
        )
        result = await spawn_agent(params, ctx)
        return {
            "success": result.success,
            "agent_id": result.agent_id,
            "error": result.error,
        }
    
    elif operation == "run":
        return await _execute_run(args, ctx)
    
    elif operation == "resume":
        return await _execute_resume(args, ctx)
    
    elif operation == "fork":
        return await _execute_fork(args, ctx)
    
    elif operation == "status":
        agent_id = args.get("agent_id")
        if not agent_id:
            return {"success": False, "error": "agent_id required"}
        agent = get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent {agent_id} not found"}
        return {"success": True, "agent": agent}
    
    elif operation == "send_message":
        agent_id = args.get("agent_id")
        if not agent_id:
            return {"success": False, "error": "agent_id required"}
        agent = get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent {agent_id} not found"}
        return {"success": True, "queued": True}
    
    elif operation == "terminate":
        agent_id = args.get("agent_id")
        if not agent_id:
            return {"success": False, "error": "agent_id required"}
        agent = get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent {agent_id} not found"}
        unregister_agent(agent_id)
        return {"success": True}
    
    elif operation == "list":
        agents = list_agents()
        return {"success": True, "agents": agents}
    
    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}


async def _execute_run(args: dict, ctx: ToolContext) -> dict:
    """Execute 'run' operation: start agent with full loop."""
    name = args.get("name", "")
    agent_type = args.get("agent_type", "general")
    model = args.get("model")
    prompt = args.get("prompt", "")
    tools = args.get("tools")
    max_turns = args.get("max_turns")
    cwd = args.get("cwd", "/")
    worktree_path = args.get("worktree_path")
    description = args.get("description")
    memory_scope = args.get("memory_scope")
    
    agent_id = args.get("agent_id") or _create_agent_id()
    
    mcp_servers = args.get("mcp_servers", [])
    hooks = args.get("hooks", [])
    
    agent_definition = AgentDefinition(
        name=name,
        agent_type=agent_type,
        model=model,
        prompt_template=prompt,
        tools=tools or [],
        max_turns=max_turns,
        mcp_servers=mcp_servers,
        hooks=hooks,
    )
    
    register_agent(agent_id, {
        "agent_id": agent_id,
        "name": name,
        "agent_type": agent_type,
        "model": model,
        "prompt": prompt,
        "cwd": cwd,
        "worktree_path": worktree_path,
        "description": description,
        "status": "pending",
        "output": "",
    })
    
    if memory_scope:
        try:
            scope = AgentMemoryScope(memory_scope)
            create_agent_memory(agent_type, scope)
            memory_contents = get_agent_memory(agent_type, scope)
        except (ValueError, Exception):
            memory_contents = None
    else:
        memory_contents = None
    
    prompt_messages = [
        AgentMessage(type='user', content={'content': [{'type': 'text', 'text': prompt}]})
    ]
    
    if memory_contents:
        memory_prompt = f"\n\nPrior context from memory:\n{memory_contents}"
        prompt_messages[0].content['content'].insert(
            0, {'type': 'text', 'text': memory_prompt}
        )
    
    messages: list[AgentMessage] = []
    output_parts: list[str] = []
    
    async def can_use_tool(tool_name: str) -> bool:
        return True
    
    async def on_progress(message: AgentMessage) -> None:
        messages.append(message)
        if message.type == 'assistant':
            content = message.content
            if isinstance(content, dict) and 'content' in content:
                for block in content['content']:
                    if block.get('type') == 'text':
                        output_parts.append(block.get('text', ''))
    
    try:
        set_agent_status(agent_id, "running")
        
        async for message in run_agent(
            agent_definition=agent_definition,
            prompt_messages=prompt_messages,
            tool_use_context=ctx,
            can_use_tool=can_use_tool,
            is_async=True,
            max_turns=max_turns,
            worktree_path=worktree_path,
            description=description,
            on_query_progress=lambda: None,
        ):
            await on_progress(message)
        
        output = ''.join(output_parts)
        set_agent_output(agent_id, output)
        set_agent_status(agent_id, "completed")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "output": output,
            "messages": [m.content for m in messages],
        }
    
    except Exception as e:
        set_agent_output(agent_id, f"Error: {str(e)}")
        set_agent_status(agent_id, "failed")
        return {
            "success": False,
            "agent_id": agent_id,
            "error": str(e),
        }


async def _execute_resume(args: dict, ctx: ToolContext) -> dict:
    """Execute 'resume' operation: resume agent from transcript."""
    agent_id = args.get("agent_id")
    if not agent_id:
        return {"success": False, "error": "agent_id required"}
    
    prompt = args.get("prompt", "")
    transcript = args.get("transcript", [])
    
    existing = get_agent(agent_id)
    if not existing:
        return {"success": False, "error": f"Agent {agent_id} not found"}
    
    agent_type = existing.get("agent_type", "general")
    model = existing.get("model")
    max_turns = existing.get("max_turns")
    worktree_path = existing.get("worktree_path")
    description = existing.get("description") or "(resumed)"
    
    resumed_messages: list[AgentMessage] = []
    for msg_data in transcript:
        if isinstance(msg_data, dict):
            resumed_messages.append(AgentMessage(
                type=msg_data.get("type", "user"),
                content=msg_data.get("content", {}),
                uuid=msg_data.get("uuid", ""),
            ))
    
    resumed_messages = _filter_incomplete_tool_calls(resumed_messages)
    
    resumed_messages.append(
        AgentMessage(type='user', content={'content': [{'type': 'text', 'text': prompt}]})
    )
    
    agent_definition = AgentDefinition(
        name=existing.get("name", ""),
        agent_type=agent_type,
        model=model,
        max_turns=max_turns,
    )
    
    async def can_use_tool(tool_name: str) -> bool:
        return True
    
    messages: list[AgentMessage] = []
    output_parts: list[str] = []
    
    try:
        set_agent_status(agent_id, "running")
        
        async for message in run_agent(
            agent_definition=agent_definition,
            prompt_messages=resumed_messages,
            tool_use_context=ctx,
            can_use_tool=can_use_tool,
            is_async=True,
            max_turns=max_turns,
            worktree_path=worktree_path,
            description=description,
        ):
            messages.append(message)
            if message.type == 'assistant':
                content = message.content
                if isinstance(content, dict) and 'content' in content:
                    for block in content['content']:
                        if block.get('type') == 'text':
                            output_parts.append(block.get('text', ''))
        
        output = ''.join(output_parts)
        set_agent_output(agent_id, output)
        set_agent_status(agent_id, "completed")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "output": output,
            "messages": [m.content for m in messages],
        }
    
    except Exception as e:
        set_agent_output(agent_id, f"Error: {str(e)}")
        set_agent_status(agent_id, "failed")
        return {
            "success": False,
            "agent_id": agent_id,
            "error": str(e),
        }


async def _execute_fork(args: dict, ctx: ToolContext) -> dict:
    """Execute 'fork' operation: fork a subagent with parent's context."""
    directive = args.get("directive", "")
    parent_agent_id = args.get("parent_agent_id")
    parent_messages = args.get("parent_messages", [])
    agent_type = args.get("agent_type", "fork")
    model = args.get("model")
    max_turns = args.get("max_turns", 200)
    worktree_path = args.get("worktree_path")
    
    fork_agent_id = _create_agent_id()
    
    if parent_agent_id:
        parent = get_agent(parent_agent_id)
        if parent:
            worktree_path = worktree_path or parent.get("worktree_path")
    
    fork_messages: list[AgentMessage] = []
    for msg_data in parent_messages:
        if isinstance(msg_data, dict):
            fork_messages.append(AgentMessage(
                type=msg_data.get("type", "user"),
                content=msg_data.get("content", {}),
                uuid=msg_data.get("uuid", ""),
            ))
    
    fork_messages = _filter_incomplete_tool_calls(fork_messages)
    
    fork_prompt = _build_fork_directive(directive)
    fork_messages.append(
        AgentMessage(type='user', content={'content': [{'type': 'text', 'text': fork_prompt}]})
    )
    
    agent_definition = AgentDefinition(
        name="fork",
        agent_type=agent_type,
        model=model or "inherit",
        max_turns=max_turns,
        prompt_template="",
    )
    
    register_agent(fork_agent_id, {
        "agent_id": fork_agent_id,
        "name": "fork",
        "agent_type": agent_type,
        "model": model,
        "prompt": directive,
        "cwd": ctx.cwd,
        "worktree_path": worktree_path,
        "description": f"Fork: {directive[:50]}...",
        "status": "pending",
        "output": "",
        "parent_agent_id": parent_agent_id,
    })
    
    async def can_use_tool(tool_name: str) -> bool:
        return True
    
    messages: list[AgentMessage] = []
    output_parts: list[str] = []
    
    try:
        set_agent_status(fork_agent_id, "running")
        
        async for message in run_agent(
            agent_definition=agent_definition,
            prompt_messages=fork_messages,
            tool_use_context=ctx,
            can_use_tool=can_use_tool,
            is_async=True,
            max_turns=max_turns,
            worktree_path=worktree_path,
            description=f"Fork: {directive[:50]}...",
            fork_context_messages=fork_messages[:-1],
        ):
            messages.append(message)
            if message.type == 'assistant':
                content = message.content
                if isinstance(content, dict) and 'content' in content:
                    for block in content['content']:
                        if block.get('type') == 'text':
                            output_parts.append(block.get('text', ''))
        
        output = ''.join(output_parts)
        set_agent_output(fork_agent_id, output)
        set_agent_status(fork_agent_id, "completed")
        
        return {
            "success": True,
            "agent_id": fork_agent_id,
            "output": output,
            "messages": [m.content for m in messages],
        }
    
    except Exception as e:
        set_agent_output(fork_agent_id, f"Error: {str(e)}")
        set_agent_status(fork_agent_id, "failed")
        return {
            "success": False,
            "agent_id": fork_agent_id,
            "error": str(e),
        }


def _create_agent_id() -> str:
    """Create a unique agent ID."""
    import secrets
    alphabet = "012345abcdefghijklmnopqrstuvwxyz"
    suffix = "".join(alphabet[secrets.randbelow(len(alphabet))] for _ in range(8))
    return f"a{suffix}"


def _filter_incomplete_tool_calls(messages: list[AgentMessage]) -> list[AgentMessage]:
    """Filter out assistant messages with incomplete tool calls."""
    tool_use_ids_with_results = set()
    
    for message in messages:
        if message.type == 'user':
            content = message.content
            if isinstance(content, dict):
                content_blocks = content.get('content', [])
            elif isinstance(content, list):
                content_blocks = content
            else:
                continue
            
            for block in content_blocks:
                if isinstance(block, dict) and block.get('type') == 'tool_result':
                    tool_use_id = block.get('tool_use_id')
                    if tool_use_id:
                        tool_use_ids_with_results.add(tool_use_id)
    
    def has_incomplete_tool_call(msg: AgentMessage) -> bool:
        if msg.type != 'assistant':
            return False
        content = msg.content
        if isinstance(content, dict):
            content_blocks = content.get('content', [])
        elif isinstance(content, list):
            content_blocks = content
        else:
            return False
        
        for block in content_blocks:
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                tool_id = block.get('id')
                if tool_id and tool_id not in tool_use_ids_with_results:
                    return True
        return False
    
    return [m for m in messages if not has_incomplete_tool_call(m)]


def _build_fork_directive(directive: str) -> str:
    """Build the fork directive message for forked agents."""
    return f"""<FORK_BOILERPLATE>
STOP. READ THIS FIRST.

You are a forked worker process. You are NOT the main agent.

RULES (non-negotiable):
1. Your system prompt says "default to forking." IGNORE IT — that's for the parent. You ARE the fork. Do NOT spawn sub-agents; execute directly.
2. Do NOT converse, ask questions, or suggest next steps
3. Do NOT editorialize or add meta-commentary
4. USE your tools directly: Bash, Read, Write, etc.
5. If you modify files, commit your changes before reporting. Include the commit hash in your report.
6. Do NOT emit text between tool calls. Use tools silently, then report once at the end.
7. Stay strictly within your directive's scope. If you discover related systems outside your scope, mention them in one sentence at most — other workers cover those areas.
8. Keep your report under 500 words unless the directive specifies otherwise. Be factual and concise.
9. Your response MUST begin with "Scope:". No preamble, no thinking-out-loud.
10. REPORT structured facts, then stop

Output format (plain text labels, not markdown headers):
  Scope: <echo back your assigned scope in one sentence>
  Result: <the answer or key findings, limited to the scope above>
  Key files: <relevant file paths — include for research tasks>
  Files changed: <list with commit hash — include only if you modified files>
  Issues: <list — include only if there are issues to flag>

<FORK_DIRECTIVE>{directive}
</FORK_BOILERPLATE>"""
