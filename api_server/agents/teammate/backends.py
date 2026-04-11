import asyncio
import json
from pathlib import Path
import time

from .executor import TeammateExecutor, TeammateSpawnConfig, TeammateSpawnResult, BackendType


def get_executor(backend_type: BackendType | None = None, storage_dir: Path | None = None) -> TeammateExecutor:
    """
    Gets a TeammateExecutor for spawning teammates.
    
    Args:
        backend_type: Explicit backend type to use. If None, uses auto-detection.
        storage_dir: Optional storage directory for mailbox files.
    
    Returns:
        TeammateExecutor instance
    """
    if backend_type is None:
        from .registry import get_teammate_executor
        return get_teammate_executor(prefer_in_process=False, storage_dir=storage_dir)
    
    if backend_type == BackendType.IN_PROCESS:
        return InProcessBackend(storage_dir)
    elif backend_type == BackendType.TMUX:
        from .tmux_backend import TmuxPaneBackend
        from .pane_executor import PaneBackendExecutor
        return PaneBackendExecutor(TmuxPaneBackend(), storage_dir)
    elif backend_type == BackendType.ITERM2:
        from .iterm_backend import ITermPaneBackend
        from .pane_executor import PaneBackendExecutor
        return PaneBackendExecutor(ITermPaneBackend(), storage_dir)
    else:
        return InProcessBackend(storage_dir)


class InProcessBackend(TeammateExecutor):
    def __init__(self, storage_dir: Path | None = None):
        self._storage_dir = storage_dir or Path.home() / ".claude" / "teams"
        self._agents: dict[str, dict] = {}
        self._mailbox_dir = self._storage_dir / "mailbox"
        self._mailbox_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def backend_type(self) -> BackendType:
        return BackendType.IN_PROCESS
    
    async def is_available(self) -> bool:
        return True
    
    async def spawn(self, config: TeammateSpawnConfig) -> TeammateSpawnResult:
        agent_id = config.identity.agent_id
        
        self._agents[agent_id] = {
            "identity": config.identity,
            "system_prompt": config.system_prompt,
            "model": config.model,
            "tools": config.tools,
            "cwd": config.cwd,
            "status": "running",
            "created_at": time.time(),
        }
        
        return TeammateSpawnResult(success=True, agent_id=agent_id)
    
    async def send_message(self, agent_id: str, message: dict) -> None:
        if agent_id not in self._agents:
            return
        
        mailbox_path = self._get_mailbox_path(agent_id)
        with open(mailbox_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(message) + "\n")
    
    async def terminate(self, agent_id: str, reason: str | None = None) -> bool:
        if agent_id not in self._agents:
            return False
        
        self._agents[agent_id]["status"] = "terminated"
        self._agents[agent_id]["terminate_reason"] = reason
        return True
    
    async def kill(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        
        self._agents[agent_id]["status"] = "killed"
        del self._agents[agent_id]
        return True
    
    async def is_active(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        return self._agents[agent_id].get("status") == "running"
    
    def _get_mailbox_path(self, agent_id: str) -> Path:
        return self._mailbox_dir / f"{agent_id}.jsonl"
    
    async def read_mailbox(self, agent_id: str, last_index: int = 0) -> tuple[list[dict], int]:
        mailbox_path = self._get_mailbox_path(agent_id)
        if not mailbox_path.exists():
            return [], last_index
        
        messages = []
        with open(mailbox_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        
        return messages[last_index:], len(messages)
    
    async def cleanup(self) -> None:
        for agent_id in list(self._agents.keys()):
            await self.kill(agent_id)


class TmuxBackend(TeammateExecutor):
    def __init__(self, storage_dir: Path | None = None):
        self._storage_dir = storage_dir or Path.home() / ".claude" / "teams"
        self._agents: dict[str, dict] = {}
    
    @property
    def backend_type(self) -> BackendType:
        return BackendType.TMUX
    
    async def is_available(self) -> bool:
        proc = await asyncio.create_subprocess_shell(
            "which tmux",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
        return proc.returncode == 0
    
    async def spawn(self, config: TeammateSpawnConfig) -> TeammateSpawnResult:
        session_name = f"cato-{config.identity.agent_id}"
        
        proc = await asyncio.create_subprocess_shell(
            f"tmux new-session -d -s {session_name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
        
        if proc.returncode != 0:
            return TeammateSpawnResult(success=False, error="Failed to create tmux session")
        
        self._agents[config.identity.agent_id] = {
            "session_name": session_name,
            "identity": config.identity,
        }
        
        return TeammateSpawnResult(success=True, agent_id=config.identity.agent_id)
    
    async def send_message(self, agent_id: str, message: dict) -> None:
        if agent_id not in self._agents:
            return
        
        session_name = self._agents[agent_id]["session_name"]
        msg_text = json.dumps(message).replace("'", "'\\''")
        
        await asyncio.create_subprocess_shell(
            f"tmux send-keys -t {session_name} '{msg_text}' Enter",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    
    async def terminate(self, agent_id: str, reason: str | None = None) -> bool:
        if agent_id not in self._agents:
            return False
        
        session_name = self._agents[agent_id]["session_name"]
        await asyncio.create_subprocess_shell(
            f"tmux kill-session -t {session_name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        del self._agents[agent_id]
        return True
    
    async def kill(self, agent_id: str) -> bool:
        return await self.terminate(agent_id)
    
    async def is_active(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        
        session_name = self._agents[agent_id]["session_name"]
        proc = await asyncio.create_subprocess_shell(
            f"tmux has-session -t {session_name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
        return proc.returncode == 0
    
    async def cleanup(self) -> None:
        for agent_id in list(self._agents.keys()):
            await self.terminate(agent_id)
