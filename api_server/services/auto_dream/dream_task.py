"""
Task state management for dream consolidation tasks.

Provides a registry for tracking running dream tasks and their state.
"""
import asyncio
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    DREAM_PHASE_STARTING,
    DREAM_PHASE_UPDATING,
    DREAM_STATUS_COMPLETED,
    DREAM_STATUS_FAILED,
    DREAM_STATUS_KILLED,
    DREAM_STATUS_RUNNING,
)
from .types import DreamTaskState, DreamTurn


_task_registry: Dict[str, DreamTaskState] = {}
_registry_lock = asyncio.Lock()


def _generate_task_id() -> str:
    return f"dream_{uuid.uuid4().hex[:12]}"


async def register_dream_task(
    sessions_reviewing: int,
    prior_mtime: float,
) -> str:
    """
    Register a new dream task.
    
    Args:
        sessions_reviewing: Number of sessions to review.
        prior_mtime: The prior consolidation timestamp.
    
    Returns:
        The task ID string.
    """
    task_id = _generate_task_id()
    
    async with _registry_lock:
        _task_registry[task_id] = DreamTaskState(
            task_id=task_id,
            status=DREAM_STATUS_RUNNING,
            phase=DREAM_PHASE_STARTING,
            sessions_reviewing=sessions_reviewing,
            files_touched=[],
            turns=[],
            prior_mtime=prior_mtime,
        )
    
    return task_id


async def add_dream_turn(
    task_id: str,
    turn: DreamTurn,
    touched_paths: List[str],
) -> None:
    """
    Add a turn to a running dream task.
    
    Args:
        task_id: The task ID.
        turn: The DreamTurn to add.
        touched_paths: File paths touched during this turn.
    """
    async with _registry_lock:
        if task_id not in _task_registry:
            return
        task = _task_registry[task_id]
        task.turns.append(turn)
        task.files_touched.extend(touched_paths)
        task.phase = DREAM_PHASE_UPDATING


async def complete_dream_task(task_id: str) -> None:
    """
    Mark a dream task as completed.
    
    Args:
        task_id: The task ID to complete.
    """
    async with _registry_lock:
        if task_id not in _task_registry:
            return
        _task_registry[task_id].status = DREAM_STATUS_COMPLETED


async def fail_dream_task(task_id: str) -> None:
    """
    Mark a dream task as failed.
    
    Args:
        task_id: The task ID to fail.
    """
    async with _registry_lock:
        if task_id not in _task_registry:
            return
        _task_registry[task_id].status = DREAM_STATUS_FAILED


async def kill_dream_task(task_id: str) -> None:
    """
    Mark a dream task as killed.
    
    Args:
        task_id: The task ID to kill.
    """
    async with _registry_lock:
        if task_id not in _task_registry:
            return
        task = _task_registry[task_id]
        task.status = DREAM_STATUS_KILLED
        if task.abort_controller:
            task.abort_controller.set()


async def get_dream_task(task_id: str) -> Optional[DreamTaskState]:
    """
    Get the state of a dream task.
    
    Args:
        task_id: The task ID.
    
    Returns:
        DreamTaskState if found, None otherwise.
    """
    async with _registry_lock:
        return _task_registry.get(task_id)


async def list_dream_tasks() -> List[DreamTaskState]:
    """
    List all dream tasks.
    
    Returns:
        List of all DreamTaskState objects.
    """
    async with _registry_lock:
        return list(_task_registry.values())


async def get_running_dream_tasks() -> List[DreamTaskState]:
    """
    Get all running dream tasks.
    
    Returns:
        List of running DreamTaskState objects.
    """
    async with _registry_lock:
        return [
            task for task in _task_registry.values()
            if task.status == DREAM_STATUS_RUNNING
        ]


def is_dream_task(task: Any) -> bool:
    """
    Check if an object is a DreamTaskState.
    
    Args:
        task: Object to check.
    
    Returns:
        True if the object is a DreamTaskState.
    """
    return isinstance(task, DreamTaskState)


async def cleanup_completed_tasks() -> None:
    """
    Remove completed, failed, and killed tasks from the registry.
    Keeps only running tasks.
    """
    async with _registry_lock:
        keys_to_remove = [
            task_id for task_id, task in _task_registry.items()
            if task.status != DREAM_STATUS_RUNNING
        ]
        for key in keys_to_remove:
            del _task_registry[key]
