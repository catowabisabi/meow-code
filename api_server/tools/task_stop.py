"""TaskStopTool — stop a running background task."""
from typing import Any, Dict

from .types import ToolDef, ToolResult, ToolContext
from .task_create import get_session_tasks


def _get_default_session_id() -> str:
    return "default"


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {"type": "string", "description": "The ID of the background task to stop"},
        "shell_id": {"type": "string", "description": "Deprecated: use task_id instead"},
        "sessionId": {"type": "string", "description": "Session ID to scope the task list"},
    },
}


async def _execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    tool_call_id = getattr(context, 'tool_call_id', '') or ""
    task_id = args.get("task_id") or args.get("shell_id")
    if not task_id:
        return ToolResult(tool_call_id=tool_call_id, output="task_id is required", is_error=True)
    
    session_id = args.get("sessionId", _get_default_session_id())
    tasks = get_session_tasks(session_id)
    task = tasks.get(task_id)
    
    if not task:
        return ToolResult(tool_call_id=tool_call_id, output=f"No task found with ID: {task_id}", is_error=True)
    
    if task.status not in ("running", "pending", "in_progress"):
        return ToolResult(tool_call_id=tool_call_id, output=f"Task {task_id} is not running (status: {task.status})", is_error=True)
    
    task.status = "stopped"
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Successfully stopped task: {task_id}",
        is_error=False,
    )


TaskStopTool = ToolDef(
    name="task_stop",
    description="Stop a running background task by ID",
    input_schema=INPUT_SCHEMA,
    is_read_only=False,
    risk_level="medium",
    execute=_execute,
)


__all__ = ["TaskStopTool"]