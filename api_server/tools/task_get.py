"""TaskGetTool — retrieve a task by ID."""
from typing import Any, Dict, Optional

from .types import ToolDef, ToolResult, ToolContext
from .task_create import get_session_tasks, Task


def _get_default_session_id() -> str:
    return "default"


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "taskId": {"type": "string", "description": "The ID of the task to retrieve"},
        "sessionId": {"type": "string", "description": "Session ID to scope the task list"},
    },
    "required": ["taskId"],
}


async def _execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    tool_call_id = getattr(context, 'tool_call_id', '') or ""
    task_id = args.get("taskId")
    if not task_id:
        return ToolResult(tool_call_id=tool_call_id, output="taskId is required", is_error=True)
    
    session_id = args.get("sessionId", _get_default_session_id())
    tasks = get_session_tasks(session_id)
    task = tasks.get(task_id)
    
    if not task:
        return ToolResult(tool_call_id=tool_call_id, output="Task not found", is_error=True)
    
    blocked_by_str = ", ".join(f"#{tid}" for tid in task.blockedBy) if task.blockedBy else ""
    blocks_str = ", ".join(f"#{tid}" for tid in task.blocks) if task.blocks else ""
    
    lines = [
        f"Task #{task.id}: {task.subject}",
        f"Status: {task.status}",
        f"Description: {task.description}",
    ]
    if task.blockedBy:
        lines.append(f"Blocked by: {blocked_by_str}")
    if task.blocks:
        lines.append(f"Blocks: {blocks_str}")
    
    import json
    return ToolResult(
        tool_call_id=tool_call_id,
        output="\n".join(lines),
        is_error=False,
    )


TaskGetTool = ToolDef(
    name="task_get",
    description="Get details of a specific task by its ID",
    input_schema=INPUT_SCHEMA,
    is_read_only=True,
    risk_level="low",
    execute=_execute,
)


__all__ = ["TaskGetTool"]