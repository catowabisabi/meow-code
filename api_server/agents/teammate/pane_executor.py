"""
PaneBackendExecutor adapts a PaneBackend to the TeammateExecutor interface.

This allows pane-based backends (tmux, iTerm2) to be used through the same
TeammateExecutor abstraction as InProcessBackend.
"""

import asyncio
import json
import os
import shutil
from pathlib import Path

from .executor import (
    BackendType,
    TeammateExecutor,
    TeammateMessage,
    TeammateSpawnConfig,
    TeammateSpawnResult,
)
from .registry import PaneBackend, _is_inside_tmux


TEAMMATE_COMMAND_ENV_VAR = "CLAUDE_CODE_TEAMMATE_COMMAND"
TEAMMATE_COLOR_ENV_VAR = "CLAUDE_CODE_AGENT_COLOR"


class PaneBackendExecutor(TeammateExecutor):
    """
    PaneBackendExecutor adapts a PaneBackend to the TeammateExecutor interface.
    
    This adapter handles:
    - spawn(): Creates a pane and sends the CLI command to it
    - send_message(): Writes to the teammate's file-based mailbox
    - terminate(): Sends a shutdown request via mailbox
    - kill(): Kills the pane via the backend
    - is_active(): Checks if the pane is still running
    """
    
    type: BackendType
    _backend: PaneBackend
    _storage_dir: Path
    _mailbox_dir: Path
    _spawned_teammates: dict[str, dict]
    _cleanup_registered: bool
    
    def __init__(self, backend: PaneBackend, storage_dir: Path | None = None):
        self._backend = backend
        self.type = backend.type
        self._storage_dir = storage_dir or Path.home() / ".claude" / "teams"
        self._mailbox_dir = self._storage_dir / "mailbox"
        self._mailbox_dir.mkdir(parents=True, exist_ok=True)
        self._spawned_teammates = {}
        self._cleanup_registered = False
    
    @property
    def backend_type(self) -> BackendType:
        return self.type
    
    async def is_available(self) -> bool:
        """Checks if the underlying pane backend is available."""
        return await self._backend.is_available()
    
    async def spawn(self, config: TeammateSpawnConfig) -> TeammateSpawnResult:
        """Spawns a teammate in a new pane."""
        agent_id = config.identity.agent_id
        name = config.identity.agent_name
        color = config.identity.color or "cyan"
        
        try:
            result = await self._backend.create_teammate_pane_in_swarm_view(name, color)
            pane_id = result["paneId"]
            is_first_teammate = result["isFirstTeammate"]
            
            inside_tmux = await _is_inside_tmux()
            
            if is_first_teammate and inside_tmux:
                await self._backend.enable_pane_border_status()
            
            binary_path = self._get_teammate_command()
            
            teammate_args = [
                f"--agent-id {agent_id}",
                f"--agent-name {name}",
                f"--team-name {config.identity.team_name}",
                f"--agent-color {color}",
                f"--parent-session-id {os.environ.get('CLAUDE_SESSION_ID', '')}",
            ]
            
            if config.model:
                teammate_args.append(f"--model {config.model}")
            
            flags_str = " ".join(teammate_args)
            working_dir = config.cwd or str(Path.cwd())
            
            spawn_command = f"cd {working_dir} && {binary_path} {flags_str}"
            
            await self._backend.send_command_to_pane(pane_id, spawn_command, not inside_tmux)
            
            self._spawned_teammates[agent_id] = {
                "pane_id": pane_id,
                "inside_tmux": inside_tmux,
            }
            
            self._write_to_mailbox(
                name,
                config.identity.team_name,
                {
                    "from": "team-lead",
                    "text": config.system_prompt,
                    "timestamp": asyncio.get_event_loop().time(),
                },
            )
            
            return TeammateSpawnResult(success=True, agent_id=agent_id)
        
        except Exception as e:
            return TeammateSpawnResult(success=False, agent_id=agent_id, error=str(e))
    
    async def send_message(self, agent_id: str, message: TeammateMessage) -> None:
        """Sends a message to a pane-based teammate via file-based mailbox."""
        parts = agent_id.rsplit("@", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid agentId format: {agent_id}. Expected format: agentName@teamName")
        
        agent_name, team_name = parts
        
        self._write_to_mailbox(
            agent_name,
            team_name,
            {
                "text": message.text,
                "from": message.from_,
                "color": getattr(message, "color", None),
                "timestamp": getattr(message, "timestamp", None) or asyncio.get_event_loop().time(),
            },
        )
    
    async def terminate(self, agent_id: str, reason: str | None = None) -> bool:
        """Gracefully terminates a pane-based teammate."""
        parts = agent_id.rsplit("@", 1)
        if len(parts) != 2:
            return False
        
        agent_name, team_name = parts
        
        shutdown_request = {
            "type": "shutdown_request",
            "request_id": f"shutdown-{agent_id}",
            "from": "team-lead",
            "reason": reason,
        }
        
        self._write_to_mailbox(
            agent_name,
            team_name,
            {
                "from": "team-lead",
                "text": json.dumps(shutdown_request),
                "timestamp": asyncio.get_event_loop().time(),
            },
        )
        
        return True
    
    async def kill(self, agent_id: str) -> bool:
        """Force kills a pane-based teammate by killing its pane."""
        teammate_info = self._spawned_teammates.get(agent_id)
        if not teammate_info:
            return False
        
        pane_id = teammate_info["pane_id"]
        inside_tmux = teammate_info["inside_tmux"]
        
        killed = await self._backend.kill_pane(pane_id, not inside_tmux)
        
        if killed:
            del self._spawned_teammates[agent_id]
        
        return killed
    
    async def is_active(self, agent_id: str) -> bool:
        """Checks if a pane-based teammate is still active."""
        return agent_id in self._spawned_teammates
    
    async def cleanup(self) -> None:
        """Cleans up all spawned panes."""
        for agent_id in list(self._spawned_teammates.keys()):
            await self.kill(agent_id)
    
    def _get_teammate_command(self) -> str:
        """Gets the command to spawn a teammate."""
        return os.environ.get(TEAMMATE_COMMAND_ENV_VAR, shutil.which("claude") or "claude")
    
    def _get_mailbox_path(self, agent_name: str, team_name: str) -> Path:
        """Gets the mailbox path for an agent."""
        return self._mailbox_dir / f"{team_name}_{agent_name}.jsonl"
    
    def _write_to_mailbox(self, agent_name: str, team_name: str, message: dict) -> None:
        """Writes a message to the teammate's mailbox."""
        mailbox_path = self._get_mailbox_path(agent_name, team_name)
        
        with open(mailbox_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(message) + "\n")
    
    async def read_mailbox(
        self,
        agent_name: str,
        team_name: str,
        last_index: int = 0,
    ) -> tuple[list[dict], int]:
        """Reads messages from a teammate's mailbox."""
        mailbox_path = self._get_mailbox_path(agent_name, team_name)
        
        if not mailbox_path.exists():
            return [], last_index
        
        messages = []
        with open(mailbox_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        
        return messages[last_index:], len(messages)


def create_pane_backend_executor(
    backend: PaneBackend,
    storage_dir: Path | None = None,
) -> PaneBackendExecutor:
    """Creates a PaneBackendExecutor wrapping the given PaneBackend."""
    return PaneBackendExecutor(backend, storage_dir)
