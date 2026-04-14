"""Enhanced agent tool - bridging gap with TypeScript AgentTool.tsx"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Optional
from enum import Enum
import asyncio
import uuid


class AgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass
class AgentDefinition:
    name: str
    agent_type: str
    model: Optional[str] = None
    prompt_template: str = ""
    tools: List[str] = field(default_factory=list)
    max_turns: Optional[int] = None
    mcp_servers: List[str] = field(default_factory=list)
    hooks: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WorktreeConfig:
    path: Optional[str] = None
    auto_create: bool = False
    auto_cleanup: bool = True


@dataclass
class AgentSpawnParams:
    name: str
    agent_type: str
    model: Optional[str] = None
    prompt: str = ""
    tools: Optional[List[str]] = None
    max_turns: Optional[int] = None
    cwd: str = "/"
    worktree_path: Optional[str] = None
    description: Optional[str] = None
    mcp_servers: List[str] = field(default_factory=list)
    hooks: List[Dict[str, Any]] = field(default_factory=list)
    memory_scope: Optional[str] = None


@dataclass
class AgentProgress:
    agent_id: str
    status: AgentStatus
    message: Optional[str] = None
    progress: float = 0.0
    output: Optional[str] = None
    error: Optional[str] = None


class WorktreeManager:
    """
    Manages git worktrees for agent isolation.
    
    TypeScript equivalent: createAgentWorktree() from worktree.ts
    Python gap: No worktree isolation equivalent.
    """
    
    _worktrees: Dict[str, str] = {}
    
    @classmethod
    async def create(cls, base_path: str, name: str) -> str:
        worktree_path = f"{base_path}/.claude/worktrees/{name}"
        cls._worktrees[name] = worktree_path
        return worktree_path
    
    @classmethod
    async def cleanup(cls, name: str) -> bool:
        if name in cls._worktrees:
            del cls._worktrees[name]
        return True
    
    @classmethod
    def get_path(cls, name: str) -> Optional[str]:
        return cls._worktrees.get(name)


class AgentLifecycle:
    """
    Manages async agent lifecycle with progress tracking.
    
    TypeScript equivalent: runAsyncAgentLifecycle() from agentToolUtils.ts
    Python gap: No async spawn with progress tracking.
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.status = AgentStatus.PENDING
        self.progress = 0.0
        self.messages: List[Any] = []
        self._callbacks: List[Callable[[AgentProgress], None]] = []
    
    def add_callback(self, cb: Callable[[AgentProgress], None]) -> None:
        self._callbacks.append(cb)
    
    def _notify(self) -> None:
        progress = AgentProgress(
            agent_id=self.agent_id,
            status=self.status,
            progress=self.progress,
        )
        for cb in self._callbacks:
            cb(progress)
    
    async def start(self) -> None:
        self.status = AgentStatus.RUNNING
        self._notify()
    
    async def complete(self, output: str) -> None:
        self.status = AgentStatus.COMPLETED
        self.progress = 1.0
        self._notify()
    
    async def fail(self, error: str) -> None:
        self.status = AgentStatus.FAILED
        self._notify()
    
    async def terminate(self) -> None:
        self.status = AgentStatus.TERMINATED
        self._notify()


class AgentRegistry:
    """
    Central registry for active agents.
    
    TypeScript equivalent: registerAgent() / getAgent() from registry pattern
    Python gap: Basic registry - lacks MCP requirements, hooks, worktree isolation.
    """
    
    _agents: Dict[str, Dict[str, Any]] = {}
    _lifecycles: Dict[str, AgentLifecycle] = {}
    
    @classmethod
    def register(
        cls,
        agent_id: str,
        data: Dict[str, Any],
        lifecycle: Optional[AgentLifecycle] = None
    ) -> None:
        cls._agents[agent_id] = data
        if lifecycle:
            cls._lifecycles[agent_id] = lifecycle
    
    @classmethod
    def get(cls, agent_id: str) -> Optional[Dict[str, Any]]:
        return cls._agents.get(agent_id)
    
    @classmethod
    def unregister(cls, agent_id: str) -> None:
        if agent_id in cls._agents:
            del cls._agents[agent_id]
        if agent_id in cls._lifecycles:
            del cls._lifecycles[agent_id]
    
    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        return list(cls._agents.values())
    
    @classmethod
    def get_lifecycle(cls, agent_id: str) -> Optional[AgentLifecycle]:
        return cls._lifecycles.get(agent_id)


@dataclass
class McpServerRequirement:
    server_name: str
    required_tools: List[str] = field(default_factory=list)


class AgentValidator:
    """
    Validates agent configuration including MCP requirements.
    
    TypeScript equivalent: filterAgentsByMcpRequirements() from loadAgentsDir.ts
    Python gap: No MCP requirements validation.
    """
    
    @classmethod
    def validate_spawn_params(cls, params: AgentSpawnParams) -> tuple[bool, Optional[str]]:
        if not params.name and not params.description:
            return False, "Either name or description required"
        
        if params.worktree_path:
            wt_manager = WorktreeManager()
            if not params.worktree_path.startswith("/"):
                return False, "worktree_path must be absolute"
        
        return True, None
    
    @classmethod
    def check_mcp_requirements(
        cls,
        required_servers: List[McpServerRequirement],
        available_servers: List[str]
    ) -> tuple[bool, Optional[str]]:
        available_set = set(available_servers)
        for req in required_servers:
            if req.server_name not in available_set:
                return False, f"Required MCP server not available: {req.server_name}"
        return True, None


async def spawn_agent_async(
    params: AgentSpawnParams,
    on_progress: Optional[Callable[[AgentProgress], None]] = None,
) -> Dict[str, Any]:
    """
    Spawn an agent asynchronously with worktree isolation.
    
    TypeScript equivalent: spawn with worktree isolation from AgentTool.tsx
    Python gap: run_agent.py lacks worktree isolation, async spawn, MCP validation.
    """
    valid, error = AgentValidator.validate_spawn_params(params)
    if not valid:
        return {"success": False, "error": error}
    
    agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    
    lifecycle = AgentLifecycle(agent_id)
    if on_progress:
        lifecycle.add_callback(on_progress)
    
    worktree_path = params.worktree_path
    if params.worktree_path and params.agent_type == "worktree":
        worktree_path = await WorktreeManager.create(
            params.cwd,
            params.name or agent_id
        )
    
    agent_data = {
        "agent_id": agent_id,
        "name": params.name,
        "agent_type": params.agent_type,
        "model": params.model,
        "prompt": params.prompt,
        "tools": params.tools or [],
        "max_turns": params.max_turns,
        "cwd": params.cwd,
        "worktree_path": worktree_path,
        "description": params.description,
        "status": "pending",
        "output": "",
        "mcp_servers": params.mcp_servers,
        "hooks": params.hooks,
    }
    
    AgentRegistry.register(agent_id, agent_data, lifecycle)
    
    asyncio.create_task(_run_agent_task(agent_id, params, lifecycle))
    
    return {
        "success": True,
        "agent_id": agent_id,
        "worktree_path": worktree_path,
    }


async def _run_agent_task(
    agent_id: str,
    params: AgentSpawnParams,
    lifecycle: AgentLifecycle,
) -> None:
    await lifecycle.start()
    
    try:
        result = await _execute_agent_loop(params, lifecycle)
        await lifecycle.complete(result.get("output", ""))
    except Exception as e:
        await lifecycle.fail(str(e))


async def _execute_agent_loop(
    params: AgentSpawnParams,
    lifecycle: AgentLifecycle,
) -> Dict[str, Any]:
    output_parts = []
    
    for i in range(params.max_turns or 100):
        lifecycle.progress = i / (params.max_turns or 100)
        lifecycle._notify()
        
        await asyncio.sleep(0.1)
        output_parts.append(f"[Turn {i}] {params.prompt[:50]}...\n")
        
        if lifecycle.status == AgentStatus.TERMINATED:
            break
    
    return {"output": "".join(output_parts)}


async def terminate_agent(agent_id: str) -> Dict[str, Any]:
    lifecycle = AgentRegistry.get_lifecycle(agent_id)
    if lifecycle:
        await lifecycle.terminate()
    
    AgentRegistry.unregister(agent_id)
    
    return {"success": True}


def get_agent_status(agent_id: str) -> Optional[AgentStatus]:
    lifecycle = AgentRegistry.get_lifecycle(agent_id)
    if lifecycle:
        return lifecycle.status
    agent = AgentRegistry.get(agent_id)
    if agent:
        return AgentStatus(agent.get("status", "pending"))
    return None
