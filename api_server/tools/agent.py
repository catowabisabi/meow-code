"""
AgentTool - Tool for spawning and managing sub-agents.

Provides methods for:
- spawn_agent: Create a new sub-agent
- send_message: Send a message to a running agent
- terminate: Gracefully terminate an agent
- kill: Force kill an agent
- list_agents: List all agents
- get_status: Get detailed agent status

Based on the TypeScript AgentTool implementation in _claude_code_leaked_source_code.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .types import ToolDef, ToolContext, ToolResult


TOOL_NAME = "Agent"


@dataclass
class AgentConfig:
    name: str
    agent_type: str = "general"
    model: Optional[str] = None
    prompt: Optional[str] = None
    tools: list[str] = field(default_factory=list)
    max_turns: Optional[int] = None
    isolation: Optional[str] = None
    cwd: Optional[str] = None
    run_in_background: bool = False
    team_name: Optional[str] = None
    mode: Optional[str] = None


@dataclass
class AgentSpawnResult:
    success: bool
    agent_id: Optional[str] = None
    output: str = ""
    error: Optional[str] = None
    status: Optional[str] = None


@dataclass
class AgentInfo:
    agent_id: str
    name: str
    agent_type: str
    status: str
    task: str
    model: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None


class AgentManager:
    _instance: Optional["AgentManager"] = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._agents: dict[str, dict] = {}
        self._queues: dict[str, asyncio.Queue] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._abort_signals: dict[str, asyncio.Event] = {}
        self._initialized = True
    
    def register_agent(self, agent_id: str, config: AgentConfig) -> None:
        self._agents[agent_id] = {
            "id": agent_id,
            "name": config.name,
            "type": config.agent_type,
            "status": "running",
            "task": config.prompt or "",
            "model": config.model,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
        }
        self._queues[agent_id] = asyncio.Queue()
        self._abort_signals[agent_id] = asyncio.Event()
    
    def get_agent(self, agent_id: str) -> Optional[dict]:
        return self._agents.get(agent_id)
    
    def list_agents(self, session_id: Optional[str] = None) -> list[dict]:
        agents = list(self._agents.values())
        if session_id:
            agents = [a for a in agents if a.get("session_id") == session_id]
        return agents
    
    def update_status(self, agent_id: str, status: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id]["status"] = status
    
    def set_result(self, agent_id: str, result: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id]["result"] = result
    
    def set_error(self, agent_id: str, error: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id]["error"] = error
    
    def remove_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        self._queues.pop(agent_id, None)
        self._tasks.pop(agent_id, None)
        self._abort_signals.pop(agent_id, None)
    
    def get_abort_signal(self, agent_id: str) -> Optional[asyncio.Event]:
        return self._abort_signals.get(agent_id)
    
    def get_queue(self, agent_id: str) -> Optional[asyncio.Queue]:
        return self._queues.get(agent_id)
    
    async def send_message(self, agent_id: str, message: str) -> bool:
        queue = self._queues.get(agent_id)
        if queue:
            await queue.put(message)
            return True
        return False


_manager: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    global _manager
    if _manager is None:
        _manager = AgentManager()
    return _manager


async def spawn_agent(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    name = args.get("name", f"agent_{uuid.uuid4().hex[:8]}")
    description = args.get("description", "")
    prompt = args.get("prompt", "")
    subagent_type = args.get("subagent_type", "general")
    model = args.get("model")
    run_in_background = args.get("run_in_background", False)
    cwd = args.get("cwd")
    isolation = args.get("isolation")
    team_name = args.get("team_name")
    mode = args.get("mode")
    
    if not prompt:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: prompt is required",
            is_error=True,
        )
    
    manager = get_agent_manager()
    
    agent_id = str(uuid.uuid4())
    
    config = AgentConfig(
        name=name,
        agent_type=subagent_type,
        model=model,
        prompt=prompt,
        run_in_background=run_in_background,
        cwd=cwd,
        isolation=isolation,
        team_name=team_name,
        mode=mode,
    )
    
    manager.register_agent(agent_id, config)
    
    if run_in_background:
        task = asyncio.create_task(
            _run_agent_async(agent_id, config, ctx)
        )
        manager._tasks[agent_id] = task
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "status": "async_launched",
                "agentId": agent_id,
                "description": description or name,
                "prompt": prompt,
                "outputFile": f"/tmp/agent_{agent_id}.output",
            }),
            is_error=False,
        )
    else:
        try:
            result = await _run_agent_sync(agent_id, config, ctx)
            return ToolResult(
                tool_call_id=tool_call_id,
                output=json.dumps({
                    "success": True,
                    "status": "completed",
                    "agentId": agent_id,
                    "result": result,
                }),
                is_error=False,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=json.dumps({
                    "success": False,
                    "error": str(e),
                }),
                is_error=True,
            )


async def _run_agent_async(agent_id: str, config: AgentConfig, ctx: ToolContext) -> None:
    manager = get_agent_manager()
    abort_signal = manager.get_abort_signal(agent_id)
    
    try:
        result = await _execute_agent(agent_id, config, ctx, abort_signal)
        manager.set_result(agent_id, result)
        manager.update_status(agent_id, "completed")
    except asyncio.CancelledError:
        manager.update_status(agent_id, "killed")
    except Exception as e:
        manager.set_error(agent_id, str(e))
        manager.update_status(agent_id, "error")


async def _run_agent_sync(agent_id: str, config: AgentConfig, ctx: ToolContext) -> str:
    manager = get_agent_manager()
    abort_signal = manager.get_abort_signal(agent_id)
    return await _execute_agent(agent_id, config, ctx, abort_signal)


async def _execute_agent(
    agent_id: str,
    config: AgentConfig,
    ctx: ToolContext,
    abort_signal: Optional[asyncio.Event],
) -> str:
    results = []
    queue = get_agent_manager().get_queue(agent_id)
    
    if queue:
        try:
            while True:
                if abort_signal and abort_signal.is_set():
                    break
                
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                    results.append(f"Message received: {msg}")
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass
    
    return "\n".join(results) if results else f"Agent {config.name} completed task: {config.prompt[:100]}"


async def send_message_to_agent(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    agent_id = args.get("agent_id", "")
    message = args.get("message", "")
    
    if not agent_id:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: agent_id is required",
            is_error=True,
        )
    
    if not message:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: message is required",
            is_error=True,
        )
    
    manager = get_agent_manager()
    agent = manager.get_agent(agent_id)
    
    if not agent:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Agent {agent_id} not found",
            is_error=True,
        )
    
    if agent["status"] != "running":
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Agent {agent_id} is not running (status: {agent['status']})",
            is_error=True,
        )
    
    success = await manager.send_message(agent_id, message)
    
    if success:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "message": f"Message queued for delivery to agent {agent_id}",
            }),
            is_error=False,
        )
    else:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Failed to send message to agent {agent_id}",
            is_error=True,
        )


async def terminate_agent(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    agent_id = args.get("agent_id", "")
    
    if not agent_id:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: agent_id is required",
            is_error=True,
        )
    
    manager = get_agent_manager()
    agent = manager.get_agent(agent_id)
    
    if not agent:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Agent {agent_id} not found",
            is_error=True,
        )
    
    abort_signal = manager.get_abort_signal(agent_id)
    if abort_signal:
        abort_signal.set()
    
    manager.update_status(agent_id, "terminating")
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=json.dumps({
            "success": True,
            "message": f"Termination requested for agent {agent_id}",
        }),
        is_error=False,
    )


async def kill_agent(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    agent_id = args.get("agent_id", "")
    
    if not agent_id:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: agent_id is required",
            is_error=True,
        )
    
    manager = get_agent_manager()
    agent = manager.get_agent(agent_id)
    
    if not agent:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Agent {agent_id} not found",
            is_error=True,
        )
    
    task = manager._tasks.get(agent_id)
    if task and not task.done():
        task.cancel()
    
    abort_signal = manager.get_abort_signal(agent_id)
    if abort_signal:
        abort_signal.set()
    
    manager.remove_agent(agent_id)
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=json.dumps({
            "success": True,
            "message": f"Agent {agent_id} killed",
        }),
        is_error=False,
    )


async def list_agents(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    session_id = args.get("session_id")
    
    manager = get_agent_manager()
    agents = manager.list_agents(session_id)
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=json.dumps({
            "success": True,
            "agents": agents,
        }),
        is_error=False,
    )


async def get_agent_status(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    agent_id = args.get("agent_id", "")
    
    if not agent_id:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: agent_id is required",
            is_error=True,
        )
    
    manager = get_agent_manager()
    agent = manager.get_agent(agent_id)
    
    if not agent:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": False,
                "error": f"Agent {agent_id} not found",
            }),
            is_error=True,
        )
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=json.dumps({
            "success": True,
            "agent": agent,
        }),
        is_error=False,
    )


AGENT_TOOL = ToolDef(
    name=TOOL_NAME,
    description="Launch a new agent to complete tasks autonomously",
    input_schema={
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "A short (3-5 word) description of the task",
            },
            "prompt": {
                "type": "string",
                "description": "The task for the agent to perform",
            },
            "subagent_type": {
                "type": "string",
                "description": "The type of specialized agent to use",
            },
            "model": {
                "type": "string",
                "enum": ["sonnet", "opus", "haiku"],
                "description": "Optional model override for this agent",
            },
            "run_in_background": {
                "type": "boolean",
                "description": "Set to true to run this agent in the background",
            },
            "name": {
                "type": "string",
                "description": "Name for the spawned agent",
            },
            "team_name": {
                "type": "string",
                "description": "Team name for spawning",
            },
            "mode": {
                "type": "string",
                "description": "Permission mode for spawned teammate",
            },
            "isolation": {
                "type": "string",
                "enum": ["worktree"],
                "description": "Isolation mode",
            },
            "cwd": {
                "type": "string",
                "description": "Absolute path to run the agent in",
            },
        },
        "required": ["prompt"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=spawn_agent,
)


SEND_MESSAGE_TO_AGENT_TOOL = ToolDef(
    name="send_message_to_agent",
    description="Send a message to a running agent",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "ID of the agent to message",
            },
            "message": {
                "type": "string",
                "description": "Message content",
            },
        },
        "required": ["agent_id", "message"],
    },
    is_read_only=True,
    risk_level="low",
    execute=send_message_to_agent,
)


TERMINATE_AGENT_TOOL = ToolDef(
    name="terminate_agent",
    description="Gracefully terminate a running agent",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "ID of the agent to terminate",
            },
        },
        "required": ["agent_id"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=terminate_agent,
)


KILL_AGENT_TOOL = ToolDef(
    name="kill_agent",
    description="Force kill an agent",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "ID of the agent to kill",
            },
        },
        "required": ["agent_id"],
    },
    is_read_only=False,
    risk_level="high",
    execute=kill_agent,
)


LIST_AGENTS_TOOL = ToolDef(
    name="list_agents",
    description="List all agents",
    input_schema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Optional session ID to filter agents",
            },
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=list_agents,
)


GET_AGENT_STATUS_TOOL = ToolDef(
    name="get_agent_status",
    description="Get detailed status of a specific agent",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "ID of the agent",
            },
        },
        "required": ["agent_id"],
    },
    is_read_only=True,
    risk_level="low",
    execute=get_agent_status,
)


__all__ = [
    "AGENT_TOOL",
    "SEND_MESSAGE_TO_AGENT_TOOL",
    "TERMINATE_AGENT_TOOL",
    "KILL_AGENT_TOOL",
    "LIST_AGENTS_TOOL",
    "GET_AGENT_STATUS_TOOL",
    "spawn_agent",
    "send_message_to_agent",
    "terminate_agent",
    "kill_agent",
    "list_agents",
    "get_agent_status",
    "AgentManager",
    "get_agent_manager",
]
