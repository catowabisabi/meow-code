from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentDefinition:
    name: str
    agent_type: str
    model: str | None = None
    prompt_template: str | None = None
    tools: list[str] = field(default_factory=list)
    max_turns: int | None = None
    mcp_servers: list[str] = field(default_factory=list)
    mcp_server_configs: dict[str, Any] = field(default_factory=dict)
    omit_claude_md: bool = False
    hooks: list[Any] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    permission_mode: str | None = None
    source: str = "user"
    effort: str | None = None
    critical_system_reminder: str | None = None


@dataclass
class AgentSpawnParams:
    name: str
    agent_type: str = "general"
    model: str | None = None
    prompt: str = ""
    tools: list[str] | None = None
    max_turns: int | None = None
    cwd: str = "/"
    worktree_path: str | None = None
    description: str | None = None


@dataclass
class AgentResult:
    success: bool
    agent_id: str | None = None
    output: str = ""
    error: str | None = None
    messages: list[dict] = field(default_factory=list)
