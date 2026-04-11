from dataclasses import dataclass
import asyncio
import time
from pathlib import Path
from typing import Callable
from .types import TaskStateBase, TaskStatus, TaskType, is_terminal_task_status

POLL_INTERVAL_MS = 1000
STOPPED_DISPLAY_MS = 3_000
PANEL_GRACE_MS = 30_000


@dataclass
class TaskAttachment:
    type: str = "task_status"
    task_id: str = ""
    tool_use_id: str | None = None
    task_type: TaskType | None = None
    status: TaskStatus | None = None
    description: str = ""
    delta_summary: str | None = None


class TaskRegistry:
    def __init__(self, storage_dir: Path | None = None):
        self._tasks: dict[str, TaskStateBase] = {}
        self._storage_dir = storage_dir or Path.home() / ".claude" / "tasks"
        self._output_dir = self._storage_dir / "output"
        self._output_dir.mkdir(parents=True, exist_ok=True)
    
    def register(self, task: TaskStateBase, existing: TaskStateBase | None = None) -> bool:
        is_replacement = existing is not None
        if existing and hasattr(existing, 'retain'):
            task = self._merge_task_state(task, existing)
        self._tasks[task.id] = task
        output_file = self._get_output_path(task.id)
        output_file.touch(exist_ok=True)
        return not is_replacement
    
    def _merge_task_state(self, new_task: TaskStateBase, existing: TaskStateBase) -> TaskStateBase:
        return TaskStateBase(
            id=new_task.id,
            type=new_task.type,
            status=new_task.status,
            description=new_task.description,
            output_file=new_task.output_file,
            output_offset=existing.output_offset if hasattr(existing, 'output_offset') else new_task.output_offset,
            start_time=existing.start_time if hasattr(existing, 'start_time') else new_task.start_time,
            end_time=new_task.end_time,
            total_paused_ms=new_task.total_paused_ms,
            notified=new_task.notified,
            tool_use_id=new_task.tool_use_id,
        )
    
    def get(self, task_id: str) -> TaskStateBase | None:
        return self._tasks.get(task_id)
    
    def get_all(self) -> dict[str, TaskStateBase]:
        return self._tasks.copy()
    
    def update(self, task_id: str, updater: Callable[[TaskStateBase], TaskStateBase]) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        updated = updater(task)
        if updated is task:
            return False
        self._tasks[task_id] = updated
        return True
    
    def delete(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        del self._tasks[task_id]
        return True
    
    def _get_output_path(self, task_id: str) -> Path:
        return self._output_dir / f"{task_id}.txt"
    
    def get_output_path(self, task_id: str) -> Path:
        return self._get_output_path(task_id)
    
    def append_output(self, task_id: str, content: str) -> int:
        output_file = self._get_output_path(task_id)
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(content)
            f.flush()
        return output_file.stat().st_size
    
    async def get_output_delta(self, task_id: str, offset: int) -> tuple[str, int]:
        output_file = self._get_output_path(task_id)
        if not output_file.exists():
            return "", offset
        stat = output_file.stat()
        if offset >= stat.st_size:
            return "", offset
        with open(output_file, "r", encoding="utf-8") as f:
            f.seek(offset)
            content = f.read()
            new_offset = f.tell()
        return content, new_offset
    
    def get_running(self) -> list[TaskStateBase]:
        return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]
    
    def evict_terminal(self, task_id: str, evict_after: float | None = None) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        if not is_terminal_task_status(task.status):
            return False
        if not task.notified:
            return False
        if evict_after is None:
            evict_after = float('inf')
        if evict_after > time.time():
            return False
        return self.delete(task_id)


_registry: TaskRegistry | None = None


def get_registry(storage_dir: Path | None = None) -> TaskRegistry:
    global _registry
    if _registry is None:
        _registry = TaskRegistry(storage_dir)
    return _registry


def register_task(task: TaskStateBase, existing: TaskStateBase | None = None) -> bool:
    return get_registry().register(task, existing)


def get_running_tasks() -> list[TaskStateBase]:
    return get_registry().get_running()


def evict_terminal_task(task_id: str, evict_after: float | None = None) -> bool:
    return get_registry().evict_terminal(task_id, evict_after)


async def poll_tasks() -> list[TaskAttachment]:
    registry = get_registry()
    attachments: list[TaskAttachment] = []
    for task in registry.get_running():
        delta, new_offset = await registry.get_output_delta(task.id, task.output_offset)
        if delta:
            task.output_offset = new_offset
            attachments.append(TaskAttachment(
                task_id=task.id,
                task_type=task.type,
                status=task.status,
                description=task.description,
                delta_summary=delta[:200],
            ))
    return attachments
