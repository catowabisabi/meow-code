from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InitializationState(Enum):
    NOT_STARTED = "not-started"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class InitializationStatus:
    status: InitializationState
    error: Exception | None = None


@dataclass
class ScopedLspServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    extension_to_language: dict[str, str] = field(default_factory=dict)
    workspace_folder: str | None = None
    initialization_options: dict[str, Any] | None = None
    max_restarts: int | None = None
    startup_timeout: int | None = None
    restart_on_crash: bool | None = None
    shutdown_timeout: int | None = None


class LspServerState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"