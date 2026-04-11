"""TODO/Task Tracking Tool — manages per-session task lists."""
from dataclasses import dataclass
from typing import Dict, List, Any

from .types import ToolDef, ToolResult, ToolContext


@dataclass
class Task:
    id: str
    content: str
    status: str  # "pending", "in_progress", "completed"


# Per-Session Storage
session_todos: Dict[str, List[Task]] = {}


def get_session_todos(session_id: str) -> List[Task]:
    """Get all tasks for a session."""
    return session_todos.get(session_id, [])


def set_session_todos(session_id: str, todos: List[Task]) -> None:
    """Set tasks for a session."""
    session_todos[session_id] = todos


# Input schema matching the TypeScript reference
INPUT_SCHEMA = {
    "type": "object",
    "required": ["action", "sessionId"],
    "properties": {
        "action": {
            "type": "string",
            "enum": ["create", "update", "list", "clear"],
            "description": "Action to perform on the task list",
        },
        "sessionId": {
            "type": "string",
            "description": "Session ID to scope the task list",
        },
        "tasks": {
            "type": "array",
            "description": "Tasks to create or update (required for create/update)",
            "items": {
                "type": "object",
                "required": ["id", "content", "status"],
                "properties": {
                    "id": {"type": "string", "description": "Unique task identifier"},
                    "content": {"type": "string", "description": "Task description"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "Task status",
                    },
                },
            },
        },
    },
}


def _parse_task(t: Dict[str, Any]) -> Task:
    """Parse a dict into a Task."""
    return Task(
        id=t.get("id", ""),
        content=t.get("content", ""),
        status=t.get("status", "pending"),
    )


async def _execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    """Execute the todo_write tool."""
    try:
        action = args.get("action")
        session_id = args.get("sessionId")
        tasks_input = args.get("tasks", [])

        if not session_id:
            return ToolResult(tool_call_id="", output="sessionId is required.", is_error=True)

        if action == "create":
            if not tasks_input:
                return ToolResult(tool_call_id="", output="tasks array is required for create action.", is_error=True)
            existing = get_session_todos(session_id)
            new_tasks = [_parse_task(t) for t in tasks_input]
            merged = existing + new_tasks
            set_session_todos(session_id, merged)
            return ToolResult(
                tool_call_id="",
                output=f"Created {len(new_tasks)} task(s). Total: {len(merged)}.",
            )

        elif action == "update":
            if not tasks_input:
                return ToolResult(tool_call_id="", output="tasks array is required for update action.", is_error=True)
            current = get_session_todos(session_id)
            update_map = {t["id"]: _parse_task(t) for t in tasks_input}
            updated = []
            for t in current:
                if t.id in update_map:
                    updated.append(update_map[t.id])
                else:
                    updated.append(t)
            # Add any tasks with new IDs
            existing_ids = {t.id for t in current}
            for t in tasks_input:
                if t.get("id") not in existing_ids:
                    updated.append(_parse_task(t))
            set_session_todos(session_id, updated)
            return ToolResult(
                tool_call_id="",
                output=f"Updated {len(tasks_input)} task(s). Total: {len(updated)}.",
            )

        elif action == "list":
            all_tasks = get_session_todos(session_id)
            if not all_tasks:
                return ToolResult(tool_call_id="", output="No tasks found for this session.")
            lines = [f"[{t.status}] {t.id}: {t.content}" for t in all_tasks]
            return ToolResult(tool_call_id="", output="\n".join(lines))

        elif action == "clear":
            prev = len(get_session_todos(session_id))
            set_session_todos(session_id, [])
            return ToolResult(tool_call_id="", output=f"Cleared {prev} task(s) from session.")

        else:
            return ToolResult(
                tool_call_id="",
                output=f"Unknown action: {action}. Use create, update, list, or clear.",
                is_error=True,
            )

    except Exception as err:
        return ToolResult(tool_call_id="", output=f"Error: {str(err)}", is_error=True)


todo_write_tool = ToolDef(
    name="todo_write",
    description="Manage a task list for the current session. Actions: create (add tasks), update (modify tasks by id), list (show all tasks), clear (remove all tasks). Tasks have id, content, and status (pending | in_progress | completed).",
    input_schema=INPUT_SCHEMA,
    is_read_only=False,
    risk_level="low",
    execute=_execute,
)
