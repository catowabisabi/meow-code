import asyncio
import json
import os
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

class CheckpointStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

@dataclass
class Checkpoint:
    id: str
    agent_id: str
    task_id: str
    state: Dict[str, Any]
    status: CheckpointStatus
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class CheckpointManager:
    def __init__(self, checkpoint_dir: Optional[str] = None):
        if checkpoint_dir is None:
            checkpoint_dir = os.path.join(
                os.path.expanduser("~"),
                ".cato",
                "checkpoints",
            )
        
        self._checkpoint_dir = checkpoint_dir
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._current_checkpoint: Optional[str] = None
        self._auto_save_interval: float = 30.0
        self._locks: Dict[str, asyncio.Lock] = {}
        
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(self._checkpoint_dir, exist_ok=True)

    def _get_checkpoint_path(self, checkpoint_id: str) -> str:
        return os.path.join(
            self._checkpoint_dir,
            f"{checkpoint_id}.json",
        )

    async def create_checkpoint(
        self,
        agent_id: str,
        task_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        checkpoint_id = str(uuid.uuid4())
        
        checkpoint = Checkpoint(
            id=checkpoint_id,
            agent_id=agent_id,
            task_id=task_id,
            state=state,
            status=CheckpointStatus.ACTIVE,
            metadata=metadata or {},
        )
        
        self._checkpoints[checkpoint_id] = checkpoint
        
        if agent_id not in self._locks:
            self._locks[agent_id] = asyncio.Lock()
        
        async with self._locks[agent_id]:
            await self._save_to_disk(checkpoint)
        
        self._current_checkpoint = checkpoint_id
        return checkpoint_id

    async def _save_to_disk(self, checkpoint: Checkpoint):
        path = self._get_checkpoint_path(checkpoint.id)
        
        data = {
            "id": checkpoint.id,
            "agent_id": checkpoint.agent_id,
            "task_id": checkpoint.task_id,
            "state": checkpoint.state,
            "status": checkpoint.status.value,
            "created_at": checkpoint.created_at,
            "completed_at": checkpoint.completed_at,
            "metadata": checkpoint.metadata,
        }
        
        with open(path, "w") as f:
            json.dump(data, f)

    async def load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Checkpoint]:
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]
        
        path = self._get_checkpoint_path(checkpoint_id)
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            checkpoint = Checkpoint(
                id=data["id"],
                agent_id=data["agent_id"],
                task_id=data["task_id"],
                state=data["state"],
                status=CheckpointStatus(data["status"]),
                created_at=data["created_at"],
                completed_at=data.get("completed_at"),
                metadata=data.get("metadata", {}),
            )
            
            self._checkpoints[checkpoint_id] = checkpoint
            return checkpoint
        except (json.JSONDecodeError, KeyError):
            return None

    async def update_checkpoint(
        self,
        checkpoint_id: str,
        state_update: Dict[str, Any],
    ) -> bool:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            return False
        
        checkpoint.state.update(state_update)
        checkpoint.created_at = time.time()
        
        await self._save_to_disk(checkpoint)
        return True

    async def complete_checkpoint(
        self,
        checkpoint_id: str,
        final_state: Optional[Dict[str, Any]] = None,
    ) -> bool:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            return False
        
        if final_state:
            checkpoint.state.update(final_state)
        
        checkpoint.status = CheckpointStatus.COMPLETED
        checkpoint.completed_at = time.time()
        
        await self._save_to_disk(checkpoint)
        
        if self._current_checkpoint == checkpoint_id:
            self._current_checkpoint = None
        
        return True

    async def fail_checkpoint(
        self,
        checkpoint_id: str,
        error: str,
    ) -> bool:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            return False
        
        checkpoint.status = CheckpointStatus.FAILED
        checkpoint.completed_at = time.time()
        checkpoint.metadata["error"] = error
        
        await self._save_to_disk(checkpoint)
        
        if self._current_checkpoint == checkpoint_id:
            self._current_checkpoint = None
        
        return True

    async def get_latest_checkpoint(
        self,
        agent_id: str,
    ) -> Optional[Checkpoint]:
        agent_checkpoints = [
            cp for cp in self._checkpoints.values()
            if cp.agent_id == agent_id
        ]
        
        if not agent_checkpoints:
            return None
        
        agent_checkpoints.sort(key=lambda cp: cp.created_at, reverse=True)
        return agent_checkpoints[0]

    async def get_checkpoints_for_task(
        self,
        task_id: str,
    ) -> List[Checkpoint]:
        return [
            cp for cp in self._checkpoints.values()
            if cp.task_id == task_id
        ]

    async def delete_checkpoint(
        self,
        checkpoint_id: str,
    ) -> bool:
        if checkpoint_id not in self._checkpoints:
            return False
        
        checkpoint = self._checkpoints[checkpoint_id]
        path = self._get_checkpoint_path(checkpoint_id)
        
        if os.path.exists(path):
            os.remove(path)
        
        del self._checkpoints[checkpoint_id]
        
        if self._current_checkpoint == checkpoint_id:
            self._current_checkpoint = None
        
        return True

    async def resume_from_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        checkpoint = await self.load_checkpoint(checkpoint_id)
        if not checkpoint:
            return None
        
        if checkpoint.status == CheckpointStatus.COMPLETED:
            return None
        
        checkpoint.status = CheckpointStatus.INTERRUPTED
        await self._save_to_disk(checkpoint)
        
        return checkpoint.state

    async def list_checkpoints(
        self,
        agent_id: Optional[str] = None,
        status: Optional[CheckpointStatus] = None,
    ) -> List[Dict[str, Any]]:
        checkpoints = list(self._checkpoints.values())
        
        if agent_id:
            checkpoints = [cp for cp in checkpoints if cp.agent_id == agent_id]
        
        if status:
            checkpoints = [cp for cp in checkpoints if cp.status == status]
        
        return [
            {
                "id": cp.id,
                "agent_id": cp.agent_id,
                "task_id": cp.task_id,
                "status": cp.status.value,
                "created_at": cp.created_at,
                "completed_at": cp.completed_at,
            }
            for cp in checkpoints
        ]

_checkpoint_manager: Optional[CheckpointManager] = None

def get_checkpoint_manager() -> CheckpointManager:
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager