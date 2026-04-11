from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Awaitable
from enum import Enum


class BackendType(str, Enum):
    TMUX = "tmux"
    ITERM2 = "iterm2"
    IN_PROCESS = "in-process"


@dataclass
class TeammateIdentity:
    agent_id: str
    agent_name: str
    team_name: str
    color: str | None = None


@dataclass
class TeammateSpawnConfig:
    identity: TeammateIdentity
    system_prompt: str
    model: str
    tools: list[dict]
    cwd: str = "/"


@dataclass
class TeammateSpawnResult:
    success: bool
    agent_id: str | None = None
    error: str | None = None


class TeammateExecutor(ABC):
    @property
    @abstractmethod
    def backend_type(self) -> BackendType:
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        pass
    
    @abstractmethod
    async def spawn(self, config: TeammateSpawnConfig) -> TeammateSpawnResult:
        pass
    
    @abstractmethod
    async def send_message(self, agent_id: str, message: dict) -> Awaitable[None]:
        pass
    
    @abstractmethod
    async def terminate(self, agent_id: str, reason: str | None = None) -> bool:
        pass
    
    @abstractmethod
    async def kill(self, agent_id: str) -> bool:
        pass
    
    @abstractmethod
    async def is_active(self, agent_id: str) -> bool:
        pass
    
    async def cleanup(self) -> None:
        pass
