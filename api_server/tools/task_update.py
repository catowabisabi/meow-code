"""TaskUpdateTool — update a task's fields."""
from typing import Any, Dict, List, Optional

from .types import ToolDef, ToolResult, ToolContext
from .task_create import get_session_tasks, Task, VALID_STATUSES


def _get_default_session_id() -> str:
    return "default"


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "taskId": {"type": "string", "description": "The ID of the task to update"},
        "subject": {"type": "string", "description": "New subject for the task"},
        "description": {"type": "string", "description": "New description for the task"},
        "activeForm": {"type": "string", "description": "Present continuous form shown in spinner when in_progress"},
        "status": {"type": "string", "description": "New status for the task", "enum": VALID_STATUSES + ["deleted"]},
        "addBlocks": {"type": "array", "items": {"type": "string"}, "description": "Task IDs that this task blocks"},
        "addBlockedBy": {"type": "array", "items": {"type": "string"}, "description": "Task IDs that block this task"},
        "owner": {"type": "string", "description": "New owner for the task"},
        "metadata": {"type": "object", "description": "Metadata keys to merge into the task. Set a key to null to delete it.", "additionalProperties": True},
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
        return ToolResult(tool_call_id=tool_call_id, output=f"Task #{task_id} not found", is_error=True)
    
    updated_fields: List[str] = []
    old_status = task.status
    
    if "subject" in args and args["subject"] != task.subject:
        task.subject = args["subject"]
        updated_fields.append("subject")
    
    if "description" in args and args["description"] != task.description:
        task.description = args["description"]
        updated_fields.append("description")
    
    if "activeForm" in args and args["activeForm"] != task.activeForm:
        task.activeForm = args["activeForm"]
        updated_fields.append("activeForm")
    
    if "owner" in args and args["owner"] != task.owner:
        task.owner = args["owner"]
        updated_fields.append("owner")
    
    if "metadata" in args:
        metadata = args["metadata"]
        for key, value in metadata.items():
            if value is None:
                task.metadata.pop(key, None)
            else:
                task.metadata[key] = value
        updated_fields.append("metadata")
    
    if "status" in args and args["status"] != task.status:
        new_status = args["status"]
        if new_status == "deleted":
            del tasks[task_id]
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Deleted task #{task_id}",
                is_error=False,
                data={"success": True, "taskId": task_id, "updatedFields": ["deleted"], "statusChange": {"from": old_status, "to": "deleted"}},
            )
        task.status = new_status
        updated_fields.append("status")
    
    if "addBlocks" in args and args["addBlocks"]:
        new_blocks = [bid for bid in args["addBlocks"] if bid not in task.blocks]
        task.blocks.extend(new_blocks)
        if new_blocks:
            updated_fields.append("blocks")
    
    if "addBlockedBy" in args and args["addBlockedBy"]:
        new_blocked = [bid for bid in args["addBlockedBy"] if bid not in task.blockedBy]
        task.blockedBy.extend(new_blocked)
        if new_blocked:
            updated_fields.append("blockedBy")
    
    if not updated_fields:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"No changes to task #{task_id}",
            is_error=False,
            data={"success": True, "taskId": task_id, "updatedFields": []},
        )
    
    import json
    status_change = {"from": old_status, "to": task.status} if "status" in updated_fields else None
    result_data = {"success": True, "taskId": task_id, "updatedFields": updated_fields}
    if status_change:
        result_data["statusChange"] = status_change
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Updated task #{task_id} {', '.join(updated_fields)}",
        is_error=False,
    )


TaskUpdateTool = ToolDef(
    name="task_update",
    description="Update a task's fields including status, subject, description, owner, and blocking relationships",
    input_schema=INPUT_SCHEMA,
    is_read_only=False,
    risk_level="low",
    execute=_execute,
)


__all__ = ["TaskUpdateTool"]