import asyncio
import uuid
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

@dataclass
class SubTask:
    id: str
    task_id: str
    description: str
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

@dataclass
class Task:
    id: str
    description: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    subtasks: List[SubTask] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class CoordinatorAgent:
    def __init__(self, message_broker=None):
        self._broker = message_broker
        self._tasks: Dict[str, Task] = {}
        self._subtasks: Dict[str, SubTask] = {}
        self._task_handlers: Dict[str, Callable] = {}
        self._agent_capabilities: Dict[str, List[str]] = {}

    def register_agent_capabilities(
        self,
        agent_id: str,
        capabilities: List[str],
    ):
        self._agent_capabilities[agent_id] = capabilities

    async def create_task(
        self,
        description: str,
        task_type: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            description=description,
            task_type=task_type,
            priority=priority,
            metadata=metadata or {},
        )
        
        self._tasks[task_id] = task
        
        if task_type in self._task_handlers:
            subtasks = await self._task_handlers[task_type](task)
            task.subtasks = subtasks
            for st in subtasks:
                self._subtasks[st.id] = st
        
        return task_id

    def register_task_handler(
        self,
        task_type: str,
        handler: Callable[[Task], Any],
    ):
        self._task_handlers[task_type] = handler

    async def decompose_task(
        self,
        task_id: str,
    ) -> List[SubTask]:
        task = self._tasks.get(task_id)
        if not task:
            return []
        
        if task.subtasks:
            return task.subtasks
        
        subtasks = []
        
        steps = self._generate_steps(task.description, task.task_type)
        
        for i, step in enumerate(steps):
            subtask = SubTask(
                id=str(uuid.uuid4()),
                task_id=task_id,
                description=step,
                priority=task.priority,
            )
            subtasks.append(subtask)
        
        task.subtasks = subtasks
        for st in subtasks:
            self._subtasks[st.id] = st
        
        return subtasks

    def _generate_steps(
        self,
        description: str,
        task_type: str,
    ) -> List[str]:
        if task_type == "code_generation":
            return [
                "Analyze requirements and constraints",
                "Design implementation approach",
                "Write code implementation",
                "Review and validate code",
                "Finalize and document",
            ]
        elif task_type == "debugging":
            return [
                "Reproduce the issue",
                "Identify root cause",
                "Implement fix",
                "Verify fix works",
                "Document resolution",
            ]
        elif task_type == "refactoring":
            return [
                "Analyze current code structure",
                "Plan refactoring approach",
                "Execute refactoring",
                "Run tests to verify",
                "Review and finalize",
            ]
        else:
            return [
                f"Analyze: {description[:50]}",
                f"Plan: {description[:50]}",
                f"Execute: {description[:50]}",
                f"Verify: {description[:50]}",
            ]

    async def assign_subtask(
        self,
        subtask_id: str,
        agent_id: str,
    ) -> bool:
        subtask = self._subtasks.get(subtask_id)
        if not subtask:
            return False
        
        subtask.assigned_agent = agent_id
        subtask.status = TaskStatus.IN_PROGRESS
        
        return True

    async def complete_subtask(
        self,
        subtask_id: str,
        result: Dict[str, Any],
    ) -> bool:
        subtask = self._subtasks.get(subtask_id)
        if not subtask:
            return False
        
        subtask.status = TaskStatus.COMPLETED
        subtask.result = result
        subtask.completed_at = time.time()
        
        await self._check_task_completion(subtask.task_id)
        
        return True

    async def fail_subtask(
        self,
        subtask_id: str,
        error: str,
    ) -> bool:
        subtask = self._subtasks.get(subtask_id)
        if not subtask:
            return False
        
        subtask.status = TaskStatus.FAILED
        subtask.error = error
        subtask.completed_at = time.time()
        
        await self._check_task_completion(subtask.task_id)
        
        return True

    async def _check_task_completion(self, task_id: str):
        task = self._tasks.get(task_id)
        if not task:
            return
        
        if not task.subtasks:
            return
        
        all_completed = all(
            st.status == TaskStatus.COMPLETED
            for st in task.subtasks
        )
        
        any_failed = any(
            st.status == TaskStatus.FAILED
            for st in task.subtasks
        )
        
        if all_completed:
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.result = {
                "subtasks_completed": len(task.subtasks),
                "results": [
                    {"id": st.id, "result": st.result}
                    for st in task.subtasks
                ],
            }
        elif any_failed:
            task.status = TaskStatus.FAILED

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        return {
            "id": task.id,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "subtasks": [
                {
                    "id": st.id,
                    "description": st.description,
                    "status": st.status.value,
                    "assigned_agent": st.assigned_agent,
                }
                for st in task.subtasks
            ],
            "created_at": task.created_at,
            "completed_at": task.completed_at,
        }

    async def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = time.time()
        
        for subtask in task.subtasks:
            if subtask.status == TaskStatus.PENDING:
                subtask.status = TaskStatus.CANCELLED
        
        return True

_coordinator: Optional[CoordinatorAgent] = None

def get_coordinator_agent() -> CoordinatorAgent:
    global _coordinator
    if _coordinator is None:
        _coordinator = CoordinatorAgent()
    return _coordinator