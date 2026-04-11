"""TodoWriteTool - Write or update a todo list."""
from typing import Dict, Any, List

from .types import ToolDef, ToolResult, ToolContext


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "todos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "status": {"type": "string", "enum": ["in_progress", "completed", "pending"]},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                }
            }
        },
        "file_path": {"type": "string", "description": "Where to save todos"},
    },
    "required": ["todos"]
}


_session_todos: Dict[str, List[Dict[str, Any]]] = {}


async def execute_todo_write(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    todos = args.get("todos", [])
    file_path = args.get("file_path")

    if not isinstance(todos, list):
        return ToolResult(tool_call_id="", output="todos must be an array", is_error=True)

    for i, todo in enumerate(todos):
        if not isinstance(todo, dict):
            return ToolResult(tool_call_id="", output=f"Todo item {i} must be an object", is_error=True)
        if "content" not in todo:
            return ToolResult(tool_call_id="", output=f"Todo item {i} missing required field 'content'", is_error=True)
        status = todo.get("status")
        if status and status not in ("in_progress", "completed", "pending"):
            return ToolResult(
                tool_call_id="",
                output=f"Invalid status '{status}'. Must be one of: in_progress, completed, pending",
                is_error=True
            )
        priority = todo.get("priority")
        if priority and priority not in ("high", "medium", "low"):
            return ToolResult(
                tool_call_id="",
                output=f"Invalid priority '{priority}'. Must be one of: high, medium, low",
                is_error=True
            )

    storage_key = file_path or "default"
    old_todos = _session_todos.get(storage_key, [])
    _session_todos[storage_key] = todos

    return ToolResult(
        tool_call_id="",
        output=f"Successfully wrote {len(todos)} todo(s). Previous: {len(old_todos)}"
    )


TOOL_TODO_WRITE = ToolDef(
    name="todo_write",
    description="Write or update a todo list",
    input_schema=INPUT_SCHEMA,
    is_read_only=False,
    risk_level="low",
    execute=execute_todo_write,
)
