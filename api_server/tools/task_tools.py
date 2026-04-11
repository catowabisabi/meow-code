"""Task tools - create, get, list, update tasks."""
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .types import ToolDef, ToolContext, ToolResult


@dataclass
class Task:
    id: str
    content: str
    status: str
    priority: str = "medium"
    created_at: int = 0


task_registry: Dict[str, Dict[str, Task]] = {}


def get_session_tasks(session_id: str) -> Dict[str, Task]:
    if session_id not in task_registry:
        task_registry[session_id] = {}
    return task_registry[session_id]


async def _task_create(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    session_id = args.get('sessionId', 'default')
    content = args.get('content', '')
    priority = args.get('priority', 'medium')
    
    if not content:
        return ToolResult(tool_call_id=tool_call_id, output="content is required", is_error=True)
    
    tasks = get_session_tasks(session_id)
    task_id = str(uuid.uuid4())[:8]
    
    tasks[task_id] = Task(
        id=task_id,
        content=content,
        status="pending",
        priority=priority,
        created_at=int(uuid.uuid1().time),
    )
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Created task {task_id}: {content}",
        is_error=False,
    )


async def _task_get(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    session_id = args.get('sessionId', 'default')
    task_id = args.get('taskId')
    
    if not task_id:
        return ToolResult(tool_call_id=tool_call_id, output="taskId is required", is_error=True)
    
    tasks = get_session_tasks(session_id)
    task = tasks.get(task_id)
    
    if not task:
        return ToolResult(tool_call_id=tool_call_id, output=f"Task {task_id} not found", is_error=True)
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"[{task.status}] {task.id}: {task.content} (priority: {task.priority})",
        is_error=False,
    )


async def _task_list(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    session_id = args.get('sessionId', 'default')
    
    tasks = get_session_tasks(session_id)
    
    if not tasks:
        return ToolResult(tool_call_id=tool_call_id, output="No tasks found", is_error=False)
    
    lines = []
    for task in tasks.values():
        lines.append(f"[{task.status}] {task.id}: {task.content} (priority: {task.priority})")
    
    return ToolResult(tool_call_id=tool_call_id, output="\n".join(lines), is_error=False)


async def _task_update(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    session_id = args.get('sessionId', 'default')
    task_id = args.get('taskId')
    status = args.get('status')
    
    if not task_id:
        return ToolResult(tool_call_id=tool_call_id, output="taskId is required", is_error=True)
    
    tasks = get_session_tasks(session_id)
    task = tasks.get(task_id)
    
    if not task:
        return ToolResult(tool_call_id=tool_call_id, output=f"Task {task_id} not found", is_error=True)
    
    if status:
        task.status = status
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Updated task {task_id}: status={task.status}",
        is_error=False,
    )


async def _task_stop(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    session_id = args.get('sessionId', 'default')
    task_id = args.get('taskId')
    
    if not task_id:
        return ToolResult(tool_call_id=tool_call_id, output="taskId is required", is_error=True)
    
    tasks = get_session_tasks(session_id)
    task = tasks.get(task_id)
    
    if not task:
        return ToolResult(tool_call_id=tool_call_id, output=f"Task {task_id} not found", is_error=True)
    
    task.status = "stopped"
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Stopped task {task_id}",
        is_error=False,
    )


TASK_CREATE_TOOL = ToolDef(
    name="task_create",
    description="Create a new task",
    input_schema={
        "type": "object",
        "properties": {
            "sessionId": {"type": "string", "description": "Session ID"},
            "content": {"type": "string", "description": "Task description"},
            "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Task priority"},
        },
        "required": ["content"],
    },
    is_read_only=False,
    risk_level="low",
    execute=_task_create,
)


TASK_GET_TOOL = ToolDef(
    name="task_get",
    description="Get details of a specific task",
    input_schema={
        "type": "object",
        "properties": {
            "sessionId": {"type": "string", "description": "Session ID"},
            "taskId": {"type": "string", "description": "Task ID"},
        },
        "required": ["taskId"],
    },
    is_read_only=True,
    risk_level="low",
    execute=_task_get,
)


TASK_LIST_TOOL = ToolDef(
    name="task_list",
    description="List all tasks for a session",
    input_schema={
        "type": "object",
        "properties": {
            "sessionId": {"type": "string", "description": "Session ID"},
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=_task_list,
)


TASK_UPDATE_TOOL = ToolDef(
    name="task_update",
    description="Update a task's status or content",
    input_schema={
        "type": "object",
        "properties": {
            "sessionId": {"type": "string", "description": "Session ID"},
            "taskId": {"type": "string", "description": "Task ID"},
            "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "stopped"], "description": "New status"},
        },
        "required": ["taskId"],
    },
    is_read_only=False,
    risk_level="low",
    execute=_task_update,
)


TASK_STOP_TOOL = ToolDef(
    name="task_stop",
    description="Stop a running task",
    input_schema={
        "type": "object",
        "properties": {
            "sessionId": {"type": "string", "description": "Session ID"},
            "taskId": {"type": "string", "description": "Task ID"},
        },
        "required": ["taskId"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=_task_stop,
)


__all__ = [
    "TASK_CREATE_TOOL",
    "TASK_GET_TOOL",
    "TASK_LIST_TOOL",
    "TASK_UPDATE_TOOL",
    "TASK_STOP_TOOL",
]
