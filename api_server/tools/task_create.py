"""TaskCreateTool — creates a new task in the task list."""
import uuid
from typing import Any, Dict, Optional

from .types import ToolDef, ToolResult, ToolContext

TASK_STATUS_PENDING = "pending"
TASK_STATUS_IN_PROGRESS = "in_progress"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_CANCELLED = "cancelled"

VALID_STATUSES = [TASK_STATUS_PENDING, TASK_STATUS_IN_PROGRESS, TASK_STATUS_COMPLETED, TASK_STATUS_FAILED, TASK_STATUS_CANCELLED]

_task_registry: Dict[str, Dict[str, "Task"]] = {}


class Task:
    def __init__(
        self,
        id: str,
        subject: str,
        description: str = "",
        status: str = TASK_STATUS_PENDING,
        activeForm: Optional[str] = None,
        owner: Optional[str] = None,
        blocks: list = None,
        blockedBy: list = None,
        metadata: Dict[str, Any] = None,
        createdAt: int = 0,
    ):
        self.id = id
        self.subject = subject
        self.description = description
        self.status = status
        self.activeForm = activeForm
        self.owner = owner
        self.blocks = blocks or []
        self.blockedBy = blockedBy or []
        self.metadata = metadata or {}
        self.createdAt = createdAt or 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "description": self.description,
            "status": self.status,
            "activeForm": self.activeForm,
            "owner": self.owner,
            "blocks": self.blocks,
            "blockedBy": self.blockedBy,
            "metadata": self.metadata,
            "createdAt": self.createdAt,
        }


def get_session_tasks(session_id: str) -> Dict[str, Task]:
    if session_id not in _task_registry:
        _task_registry[session_id] = {}
    return _task_registry[session_id]


def _get_default_session_id() -> str:
    return "default"


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "A brief title for the task"},
        "description": {"type": "string", "description": "What needs to be done"},
        "activeForm": {"type": "string", "description": "Present continuous form shown in spinner when in_progress"},
        "sessionId": {"type": "string", "description": "Session ID to scope the task list"},
        "metadata": {"type": "object", "description": "Arbitrary metadata to attach to the task", "additionalProperties": True},
    },
    "required": ["subject"],
}


async def _execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    tool_call_id = getattr(context, 'tool_call_id', '') or ""
    subject = args.get("subject")
    if not subject:
        return ToolResult(tool_call_id=tool_call_id, output="Subject is required", is_error=True)
    
    description = args.get("description", "")
    active_form = args.get("activeForm")
    session_id = args.get("sessionId", _get_default_session_id())
    metadata = args.get("metadata", {})
    
    tasks = get_session_tasks(session_id)
    task_id = str(uuid.uuid4())[:8]
    
    task = Task(
        id=task_id,
        subject=subject,
        description=description,
        status=TASK_STATUS_PENDING,
        activeForm=active_form,
        owner=None,
        blocks=[],
        blockedBy=[],
        metadata=metadata,
        createdAt=0,
    )
    
    tasks[task_id] = task
    
    import json
    task_data = {"id": task_id, "subject": subject}
    return ToolResult(
        tool_call_id=tool_call_id,
        output=json.dumps({"task": task_data}),
        is_error=False,
    )


TaskCreateTool = ToolDef(
    name="task_create",
    description="Create a new task in the task list with a subject and optional description, status, and metadata.",
    input_schema=INPUT_SCHEMA,
    is_read_only=False,
    risk_level="low",
    execute=_execute,
)


__all__ = ["TaskCreateTool", "Task", "get_session_tasks"]