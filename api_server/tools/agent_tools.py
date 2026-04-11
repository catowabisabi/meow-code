"""
AgentTool - Tool for spawning and managing sub-agents.

This module provides the AgentTool with methods for:
- spawn_agent: Create a new sub-agent with configuration
- send_message: Send a message to a running agent
- terminate: Gracefully terminate an agent
- get_status: Get agent status
- kill: Force kill an agent
- list_agents: List all agents

Based on the TypeScript AgentTool implementation in _claude_code_leaked_source_code.
"""
import asyncio
import json
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional

from ..models.message import Message
from ..models.tool import ToolResult as ModelToolResult
from ..services.agent_pool import AgentPool, AgentType, AgentStatus, agent_pool
from .types import ToolDef, ToolContext, ToolResult


# ─── Constants ─────────────────────────────────────────────────────────────────

TOOL_NAME = "Agent"
TOOL_DESCRIPTION = "Launch a new agent to complete tasks autonomously"

SPAWN_TOOL_NAME = "spawn_agent"
SPAWN_TOOL_DESCRIPTION = "Spawn a new sub-agent to perform a task"

SEND_MESSAGE_TOOL_NAME = "send_message_to_agent"
SEND_MESSAGE_TOOL_DESCRIPTION = "Send a message to a running agent"

TERMINATE_TOOL_NAME = "terminate_agent"
TERMINATE_TOOL_DESCRIPTION = "Gracefully terminate a running agent"

KILL_TOOL_NAME = "kill_agent"
KILL_TOOL_DESCRIPTION = "Force kill an agent"

LIST_AGENTS_TOOL_NAME = "list_agents"
LIST_AGENTS_TOOL_DESCRIPTION = "List all agents with their status"

GET_STATUS_TOOL_NAME = "get_agent_status"
GET_STATUS_TOOL_DESCRIPTION = "Get detailed status of a specific agent"


# ─── Agent Configuration ───────────────────────────────────────────────────────

@dataclass
class AgentConfig:
    """Configuration for spawning an agent."""
    name: str
    agent_type: AgentType = "general"
    model: Optional[str] = None
    prompt: Optional[str] = None
    tools: list[str] = field(default_factory=list)
    max_turns: Optional[int] = None
    isolation: Optional[str] = None  # "worktree" or None
    cwd: Optional[str] = None
    run_in_background: bool = False
    team_name: Optional[str] = None
    mode: Optional[str] = None  # Permission mode: "plan", "bypassPermissions", etc.


@dataclass
class AgentSpawnResult:
    """Result from spawning an agent."""
    success: bool
    agent_id: Optional[str] = None
    output: str = ""
    error: Optional[str] = None
    status: Optional[str] = None  # "completed", "async_launched", "teammate_spawned", etc.


@dataclass
class ToolProgressCallback:
    """Callback for progress updates from agent execution."""
    callback: Callable[[dict], None]
    tool_use_id: Optional[str] = None


# ─── AgentTool Implementation ───────────────────────────────────────────────────

class AgentTool:
    """
    AgentTool provides methods for spawning and managing sub-agents.
    
    This class manages the lifecycle of sub-agents including:
    - Spawning new agents with configuration
    - Inter-agent message passing
    - Agent termination and cleanup
    - Status tracking
    """
    
    def __init__(self, pool: Optional[AgentPool] = None):
        """
        Initialize the AgentTool.
        
        Args:
            pool: Optional AgentPool instance. If not provided, uses the global instance.
        """
        self._pool = pool or agent_pool
        self._message_queues: dict[str, asyncio.Queue] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._abort_signals: dict[str, asyncio.Event] = {}
    
    async def initialize(self) -> None:
        """Initialize the agent pool."""
        await self._pool.initialize()
    
    # ─── Core Agent Operations ─────────────────────────────────────────────────
    
    async def spawn_agent(
        self,
        config: AgentConfig,
        prompt: str,
        cwd: str = "/",
        parent_session_id: Optional[str] = None,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> AgentSpawnResult:
        """
        Spawn a new sub-agent with the given configuration.
        
        Args:
            config: Agent configuration
            prompt: The task prompt for the agent
            cwd: Working directory for the agent
            parent_session_id: Parent session that spawned this agent
            on_progress: Optional callback for progress updates
            
        Returns:
            AgentSpawnResult with success status and agent ID
        """
        try:
            agent_id = str(uuid.uuid4())
            
            # Determine effective model
            model = config.model or "sonnet"
            
            # Determine provider (default)
            provider = "anthropic"
            
            # Create abort signal for this agent
            abort_signal = asyncio.Event()
            self._abort_signals[agent_id] = abort_signal
            
            # Spawn agent in pool
            agent = await self._pool.spawn_agent(
                parent_session_id=parent_session_id or "",
                name=config.name,
                agent_type=config.agent_type,
                task=prompt,
                model=model,
                provider=provider,
            )
            
            # Create message queue for this agent
            self._message_queues[agent_id] = asyncio.Queue()
            
            # Handle background vs sync execution
            if config.run_in_background:
                # Background execution - run agent task in background
                task = asyncio.create_task(
                    self._run_agent_background(
                        agent_id=agent.id,
                        abort_signal=abort_signal,
                        on_progress=on_progress,
                    )
                )
                self._running_tasks[agent_id] = task
                
                return AgentSpawnResult(
                    success=True,
                    agent_id=agent.id,
                    output=f"Agent {config.name} spawned in background",
                    status="async_launched",
                )
            else:
                # Sync execution - run agent and return result
                try:
                    result = await self._pool.run_agent(
                        agent_id=agent.id,
                        abort_signal=abort_signal,
                    )
                    
                    # Clean up
                    self._cleanup_agent(agent_id)
                    
                    return AgentSpawnResult(
                        success=True,
                        agent_id=agent.id,
                        output=result,
                        status="completed",
                    )
                except Exception as e:
                    self._cleanup_agent(agent_id)
                    return AgentSpawnResult(
                        success=False,
                        agent_id=agent.id,
                        error=str(e),
                        status="error",
                    )
                    
        except Exception as e:
            return AgentSpawnResult(
                success=False,
                error=f"Failed to spawn agent: {str(e)}",
            )
    
    async def _run_agent_background(
        self,
        agent_id: str,
        abort_signal: asyncio.Event,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> None:
        """
        Run an agent in background mode.
        
        Args:
            agent_id: ID of the agent to run
            abort_signal: Abort signal for cancellation
            on_progress: Optional progress callback
        """
        try:
            # Update agent status to running
            agent = await self._pool.get_agent_async(agent_id)
            if agent:
                agent.status = "running"
                await self._pool._save_agent(agent)
            
            # Run the agent
            result = await self._pool.run_agent(
                agent_id=agent_id,
                abort_signal=abort_signal,
            )
            
            # Update agent with result
            agent = await self._pool.get_agent_async(agent_id)
            if agent:
                agent.status = "completed"
                agent.result = result
                await self._pool._save_agent(agent)
            
            # Send completion notification
            if on_progress:
                on_progress({
                    "type": "agent_completed",
                    "agent_id": agent_id,
                    "result": result,
                })
                
        except asyncio.CancelledError:
            # Agent was cancelled
            agent = await self._pool.get_agent_async(agent_id)
            if agent:
                agent.status = "killed"
                await self._pool._save_agent(agent)
                
        except Exception as e:
            # Agent failed
            agent = await self._pool.get_agent_async(agent_id)
            if agent:
                agent.status = "error"
                agent.error = str(e)
                await self._pool._save_agent(agent)
    
    async def send_message(
        self,
        agent_id: str,
        message: str,
    ) -> dict:
        """
        Send a message to a running agent.
        
        Args:
            agent_id: ID of the agent to message
            message: Message content
            
        Returns:
            Dict with success status
        """
        # Check if agent exists
        agent = await self._pool.get_agent_async(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent {agent_id} not found"}
        
        # Check if agent is running
        if agent.status != "running":
            return {
                "success": False,
                "error": f"Agent {agent_id} is not running (status: {agent.status})"
            }
        
        # Add message to queue
        if agent_id in self._message_queues:
            await self._message_queues[agent_id].put(message)
        
        # Also add to agent's message history
        agent.messages.append(Message(
            role="user",
            content=message,
        ))
        await self._pool._save_agent(agent)
        
        return {"success": True, "message": "Message sent"}
    
    async def get_status(self, agent_id: str) -> dict:
        """
        Get the status of an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Dict with agent status information
        """
        agent = await self._pool.get_agent_async(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent {agent_id} not found"}
        
        return {
            "success": True,
            "agent": {
                "id": agent.id,
                "name": agent.name,
                "type": agent.type,
                "status": agent.status,
                "task": agent.task,
                "model": agent.model,
                "provider": agent.provider,
                "result": agent.result,
                "error": agent.error,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
            },
        }
    
    async def terminate(self, agent_id: str) -> dict:
        """
        Gracefully terminate an agent.
        
        This signals the agent to stop but allows it to finish its current operation.
        
        Args:
            agent_id: ID of the agent to terminate
            
        Returns:
            Dict with success status
        """
        agent = await self._pool.get_agent_async(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent {agent_id} not found"}
        
        # Signal abort
        if agent_id in self._abort_signals:
            self._abort_signals[agent_id].set()
        
        # Update status
        agent.status = "terminating"
        await self._pool._save_agent(agent)
        
        # Cancel background task if exists
        if agent_id in self._running_tasks:
            task = self._running_tasks[agent_id]
            if not task.done():
                task.cancel()
        
        return {"success": True, "message": f"Agent {agent_id} termination requested"}
    
    async def kill(self, agent_id: str) -> dict:
        """
        Force kill an agent immediately.
        
        Args:
            agent_id: ID of the agent to kill
            
        Returns:
            Dict with success status
        """
        # Cancel background task if exists
        if agent_id in self._running_tasks:
            task = self._running_tasks[agent_id]
            if not task.done():
                task.cancel()
            del self._running_tasks[agent_id]
        
        # Signal abort
        if agent_id in self._abort_signals:
            self._abort_signals[agent_id].set()
            del self._abort_signals[agent_id]
        
        # Clean up message queue
        if agent_id in self._message_queues:
            del self._message_queues[agent_id]
        
        # Remove from pool
        await self._pool.remove_agent(agent_id)
        
        return {"success": True, "message": f"Agent {agent_id} killed"}
    
    def list_agents(self, session_id: Optional[str] = None) -> list[dict]:
        """
        List all agents, optionally filtered by session.
        
        Args:
            session_id: Optional parent session ID to filter by
            
        Returns:
            List of agent dictionaries
        """
        agents = self._pool.list_agents(session_id)
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "type": agent.type,
                "status": agent.status,
                "task": agent.task,
                "model": agent.model,
                "provider": agent.provider,
                "result": agent.result,
                "error": agent.error,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
            }
            for agent in agents
        ]
    
    def _cleanup_agent(self, agent_id: str) -> None:
        """Clean up all resources associated with an agent."""
        if agent_id in self._running_tasks:
            del self._running_tasks[agent_id]
        if agent_id in self._abort_signals:
            del self._abort_signals[agent_id]
        if agent_id in self._message_queues:
            del self._message_queues[agent_id]


# ─── Global Instance ────────────────────────────────────────────────────────────

_agent_tool: Optional[AgentTool] = None


def get_agent_tool() -> AgentTool:
    """Get the global AgentTool instance."""
    global _agent_tool
    if _agent_tool is None:
        _agent_tool = AgentTool()
    return _agent_tool


# ─── Tool Functions ─────────────────────────────────────────────────────────────

async def spawn_agent_tool(args: dict, ctx: ToolContext) -> ModelToolResult:
    """
    Tool handler for spawning an agent.
    
    Args:
        args: Tool arguments including name, agent_type, prompt, model, etc.
        ctx: Tool execution context
        
    Returns:
        ToolResult with spawn status
    """
    tool = get_agent_tool()
    await tool.initialize()
    
    config = AgentConfig(
        name=args.get("name", f"agent_{secrets.token_hex(4)}"),
        agent_type=args.get("subagent_type", "general"),
        model=args.get("model"),
        prompt=args.get("prompt"),
        tools=args.get("tools", []),
        max_turns=args.get("max_turns"),
        isolation=args.get("isolation"),
        cwd=args.get("cwd"),
        run_in_background=args.get("run_in_background", False),
        team_name=args.get("team_name"),
        mode=args.get("mode"),
    )
    
    result = await tool.spawn_agent(
        config=config,
        prompt=args.get("prompt", ""),
        cwd=args.get("cwd", "/"),
        parent_session_id=args.get("parent_session_id"),
        on_progress=ctx.on_progress,
    )
    
    output = {
        "success": result.success,
        "agent_id": result.agent_id,
        "output": result.output,
        "error": result.error,
        "status": result.status,
    }
    
    return ModelToolResult(
        tool_call_id="",
        output=json.dumps(output),
        is_error=not result.success,
    )


async def send_message_tool(args: dict, ctx: ToolContext) -> ModelToolResult:
    """
    Tool handler for sending a message to an agent.
    
    Args:
        args: Tool arguments including agent_id and message
        ctx: Tool execution context
        
    Returns:
        ToolResult with send status
    """
    tool = get_agent_tool()
    await tool.initialize()
    
    agent_id = args.get("agent_id")
    message = args.get("message", "")
    
    if not agent_id:
        return ModelToolResult(
            tool_call_id="",
            output=json.dumps({"success": False, "error": "agent_id is required"}),
            is_error=True,
        )
    
    result = await tool.send_message(agent_id, message)
    
    return ModelToolResult(
        tool_call_id="",
        output=json.dumps(result),
        is_error=not result.get("success", False),
    )


async def terminate_agent_tool(args: dict, ctx: ToolContext) -> ModelToolResult:
    """
    Tool handler for terminating an agent.
    
    Args:
        args: Tool arguments including agent_id
        ctx: Tool execution context
        
    Returns:
        ToolResult with terminate status
    """
    tool = get_agent_tool()
    await tool.initialize()
    
    agent_id = args.get("agent_id")
    
    if not agent_id:
        return ModelToolResult(
            tool_call_id="",
            output=json.dumps({"success": False, "error": "agent_id is required"}),
            is_error=True,
        )
    
    result = await tool.terminate(agent_id)
    
    return ModelToolResult(
        tool_call_id="",
        output=json.dumps(result),
        is_error=not result.get("success", False),
    )


async def kill_agent_tool(args: dict, ctx: ToolContext) -> ModelToolResult:
    """
    Tool handler for killing an agent.
    
    Args:
        args: Tool arguments including agent_id
        ctx: Tool execution context
        
    Returns:
        ToolResult with kill status
    """
    tool = get_agent_tool()
    await tool.initialize()
    
    agent_id = args.get("agent_id")
    
    if not agent_id:
        return ModelToolResult(
            tool_call_id="",
            output=json.dumps({"success": False, "error": "agent_id is required"}),
            is_error=True,
        )
    
    result = await tool.kill(agent_id)
    
    return ModelToolResult(
        tool_call_id="",
        output=json.dumps(result),
        is_error=not result.get("success", False),
    )


async def list_agents_tool(args: dict, ctx: ToolContext) -> ModelToolResult:
    """
    Tool handler for listing agents.
    
    Args:
        args: Tool arguments (optional session_id filter)
        ctx: Tool execution context
        
    Returns:
        ToolResult with list of agents
    """
    tool = get_agent_tool()
    await tool.initialize()
    
    session_id = args.get("session_id")
    agents = tool.list_agents(session_id)
    
    return ModelToolResult(
        tool_call_id="",
        output=json.dumps({"success": True, "agents": agents}),
        is_error=False,
    )


async def get_agent_status_tool(args: dict, ctx: ToolContext) -> ModelToolResult:
    """
    Tool handler for getting agent status.
    
    Args:
        args: Tool arguments including agent_id
        ctx: Tool execution context
        
    Returns:
        ToolResult with agent status
    """
    tool = get_agent_tool()
    await tool.initialize()
    
    agent_id = args.get("agent_id")
    
    if not agent_id:
        return ModelToolResult(
            tool_call_id="",
            output=json.dumps({"success": False, "error": "agent_id is required"}),
            is_error=True,
        )
    
    result = await tool.get_status(agent_id)
    
    return ModelToolResult(
        tool_call_id="",
        output=json.dumps(result),
        is_error=not result.get("success", False),
    )


# ─── Tool Definitions ───────────────────────────────────────────────────────────

SPAWN_AGENT_TOOL = ToolDef(
    name=SPAWN_TOOL_NAME,
    description=SPAWN_TOOL_DESCRIPTION,
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name for the spawned agent",
            },
            "description": {
                "type": "string",
                "description": "Short description of the task",
            },
            "prompt": {
                "type": "string",
                "description": "The task for the agent to perform",
            },
            "subagent_type": {
                "type": "string",
                "description": "Type of agent: explore, plan, general, verify",
                "enum": ["explore", "plan", "general", "verify"],
            },
            "model": {
                "type": "string",
                "description": "Model to use (sonnet, opus, haiku)",
                "enum": ["sonnet", "opus", "haiku"],
            },
            "run_in_background": {
                "type": "boolean",
                "description": "Run the agent in background",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the agent",
            },
            "isolation": {
                "type": "string",
                "description": "Isolation mode: worktree",
                "enum": ["worktree"],
            },
            "team_name": {
                "type": "string",
                "description": "Team name for spawning",
            },
            "mode": {
                "type": "string",
                "description": "Permission mode",
            },
            "tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of allowed tools",
            },
            "max_turns": {
                "type": "integer",
                "description": "Maximum turns for the agent",
            },
        },
        "required": ["prompt"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=spawn_agent_tool,
)

SEND_MESSAGE_TOOL = ToolDef(
    name=SEND_MESSAGE_TOOL_NAME,
    description=SEND_MESSAGE_TOOL_DESCRIPTION,
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
    execute=send_message_tool,
)

TERMINATE_AGENT_TOOL = ToolDef(
    name=TERMINATE_TOOL_NAME,
    description=TERMINATE_TOOL_DESCRIPTION,
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
    is_read_only=True,
    risk_level="medium",
    execute=terminate_agent_tool,
)

KILL_AGENT_TOOL = ToolDef(
    name=KILL_TOOL_NAME,
    description=KILL_TOOL_DESCRIPTION,
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
    execute=kill_agent_tool,
)

LIST_AGENTS_TOOL = ToolDef(
    name=LIST_AGENTS_TOOL_NAME,
    description=LIST_AGENTS_TOOL_DESCRIPTION,
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
    execute=list_agents_tool,
)

GET_AGENT_STATUS_TOOL = ToolDef(
    name=GET_STATUS_TOOL_NAME,
    description=GET_STATUS_TOOL_DESCRIPTION,
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
    execute=get_agent_status_tool,
)

# Combined tool list
AGENT_TOOLS = [
    SPAWN_AGENT_TOOL,
    SEND_MESSAGE_TOOL,
    TERMINATE_AGENT_TOOL,
    KILL_AGENT_TOOL,
    LIST_AGENTS_TOOL,
    GET_AGENT_STATUS_TOOL,
]


# ─── Convenience Functions ─────────────────────────────────────────────────────

async def agent_spawn(
    name: str,
    agent_type: str = "general",
    prompt: str = "",
    model: Optional[str] = None,
    tools: Optional[list[str]] = None,
    max_turns: Optional[int] = None,
    cwd: str = "/",
    run_in_background: bool = False,
) -> AgentSpawnResult:
    """
    Convenience function to spawn an agent.
    
    Args:
        name: Agent name
        agent_type: Type of agent
        prompt: Task prompt
        model: Model to use
        tools: Allowed tools
        max_turns: Max iterations
        cwd: Working directory
        run_in_background: Run in background
        
    Returns:
        AgentSpawnResult
    """
    tool = get_agent_tool()
    await tool.initialize()
    
    config = AgentConfig(
        name=name,
        agent_type=agent_type,
        model=model,
        prompt=prompt,
        tools=tools or [],
        max_turns=max_turns,
        run_in_background=run_in_background,
    )
    
    return await tool.spawn_agent(config, prompt, cwd)


async def agent_status(agent_id: str) -> dict:
    """Get agent status."""
    tool = get_agent_tool()
    await tool.initialize()
    return await tool.get_status(agent_id)


async def agent_send_message(agent_id: str, message: str) -> dict:
    """Send message to agent."""
    tool = get_agent_tool()
    await tool.initialize()
    return await tool.send_message(agent_id, message)


async def agent_terminate(agent_id: str) -> dict:
    """Terminate an agent gracefully."""
    tool = get_agent_tool()
    await tool.initialize()
    return await tool.terminate(agent_id)


async def agent_kill(agent_id: str) -> dict:
    """Kill an agent forcefully."""
    tool = get_agent_tool()
    await tool.initialize()
    return await tool.kill(agent_id)


async def agent_list(session_id: Optional[str] = None) -> list[dict]:
    """List all agents."""
    tool = get_agent_tool()
    await tool.initialize()
    return tool.list_agents(session_id)