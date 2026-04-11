"""
Task types - ported from src/Task.ts
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable
import secrets

class TaskType(str, Enum):
    """Task type enumeration"""
    LOCAL_BASH = "local_bash"
    LOCAL_AGENT = "local_agent"
    REMOTE_AGENT = "remote_agent"
    IN_PROCESS_TEAMMATE = "in_process_teammate"
    LOCAL_WORKFLOW = "local_workflow"
    MONITOR_MCP = "monitor_mcp"
    DREAM = "dream"


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


def is_terminal_task_status(status: TaskStatus) -> bool:
    """
    True when a task is in a terminal state and will not transition further.
    Used to guard against injecting messages into dead teammates, evicting
    finished tasks from AppState, and orphan-cleanup paths.
    """
    return status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.KILLED)


@dataclass
class TaskStateBase:
    """Base fields shared by all task states"""
    id: str
    type: TaskType
    status: TaskStatus
    description: str
    output_file: str
    output_offset: int = 0
    start_time: float = field(default_factory=lambda: __import__("time").time())
    end_time: float | None = None
    total_paused_ms: int = 0
    notified: bool = False
    tool_use_id: str | None = None


@dataclass
class LocalShellSpawnInput:
    """Input for spawning a local shell task"""
    command: str
    description: str
    timeout: int | None = None
    tool_use_id: str | None = None
    agent_id: str | None = None
    kind: str = "bash"  # 'bash' | 'monitor'


@dataclass
class TaskHandle:
    """Handle for managing a task"""
    task_id: str
    cleanup: Callable[[], None] | None = None


# Task ID prefixes
_TASK_ID_PREFIXES: dict[str, str] = {
    TaskType.LOCAL_BASH: "b",         # Keep as 'b' for backward compatibility
    TaskType.LOCAL_AGENT: "a",
    TaskType.REMOTE_AGENT: "r",
    TaskType.IN_PROCESS_TEAMMATE: "t",
    TaskType.LOCAL_WORKFLOW: "w",
    TaskType.MONITOR_MCP: "m",
    TaskType.DREAM: "d",
}

# Case-insensitive-safe alphabet (digits + lowercase) for task IDs.
# 36^8 ≈ 2.8 trillion combinations, sufficient to resist brute-force symlink attacks.
_TASK_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def _get_task_id_prefix(task_type: TaskType) -> str:
    """Get task ID prefix for a task type"""
    return _TASK_ID_PREFIXES.get(task_type, "x")


def generate_task_id(task_type: TaskType) -> str:
    prefix = _get_task_id_prefix(task_type)
    suffix = "".join(_TASK_ID_ALPHABET[secrets.randbelow(len(_TASK_ID_ALPHABET))] for _ in range(8))
    return f"{prefix}{suffix}"
