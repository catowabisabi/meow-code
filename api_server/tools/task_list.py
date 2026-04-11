"""TaskListTool — list all tasks."""
from typing import Any, Dict, List

from .types import ToolDef, ToolResult, ToolContext
from .task_create import get_session_tasks


def _get_default_session_id() -> str:
    return "default"


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "sessionId": {"type": "string", "description": "Session ID to scope the task list"},
    },
}


async def _execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    tool_call_id = getattr(context, 'tool_call_id', '') or ""
    session_id = args.get("sessionId", _get_default_session_id())
    
    tasks = get_session_tasks(session_id)
    all_tasks = list(tasks.values())
    
    if not all_tasks:
        return ToolResult(tool_call_id=tool_call_id, output="No tasks found", is_error=False)
    
    resolved_ids = {t.id for t in all_tasks if t.status == "completed"}
    
    task_lines = []
    for task in all_tasks:
        owner_str = f" ({task.owner})" if task.owner else ""
        blocked_str = ""
        if task.blockedBy:
            filtered = [bid for bid in task.blockedBy if bid not in resolved_ids]
            if filtered:
                blocked_str = f" [blocked by {', '.join(f'#{bid}' for bid in filtered)}]"
        task_lines.append(f"#{task.id} [{task.status}] {task.subject}{owner_str}{blocked_str}")
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output="\n".join(task_lines),
        is_error=False,
    )


TaskListTool = ToolDef(
    name="task_list",
    description="List all tasks in the task list",
    input_schema=INPUT_SCHEMA,
    is_read_only=True,
    risk_level="low",
    execute=_execute,
)


__all__ = ["TaskListTool"]