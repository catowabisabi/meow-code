"""TaskOutputTool — retrieve output from a background task."""
import asyncio
from typing import Any, Dict

from .types import ToolDef, ToolResult, ToolContext
from .task_create import get_session_tasks


def _get_default_session_id() -> str:
    return "default"


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {"type": "string", "description": "The task ID to get output from"},
        "block": {"type": "boolean", "description": "Whether to wait for completion", "default": True},
        "timeout": {"type": "number", "description": "Max wait time in ms", "default": 30000},
        "sessionId": {"type": "string", "description": "Session ID to scope the task list"},
    },
    "required": ["task_id"],
}


async def _wait_for_completion(task_id: str, session_id: str, timeout_ms: int, abort_signal) -> Dict[str, Any]:
    start_time = asyncio.get_event_loop().time() * 1000
    while True:
        if abort_signal and abort_signal():
            return {"retrieval_status": "timeout", "task": None}
        tasks = get_session_tasks(session_id)
        task = tasks.get(task_id)
        if not task:
            return {"retrieval_status": "timeout", "task": None}
        if task.status not in ("running", "pending", "in_progress"):
            return {"retrieval_status": "success", "task": task.to_dict()}
        if asyncio.get_event_loop().time() * 1000 - start_time > timeout_ms:
            return {"retrieval_status": "timeout", "task": task.to_dict()}
        await asyncio.sleep(0.1)


async def _execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    tool_call_id = getattr(context, 'tool_call_id', '') or ""
    task_id = args.get("task_id")
    if not task_id:
        return ToolResult(tool_call_id=tool_call_id, output="task_id is required", is_error=True)
    
    session_id = args.get("sessionId", _get_default_session_id())
    tasks = get_session_tasks(session_id)
    task = tasks.get(task_id)
    
    if not task:
        return ToolResult(tool_call_id=tool_call_id, output=f"No task found with ID: {task_id}", is_error=True)
    
    block = args.get("block", True)
    timeout = args.get("timeout", 30000)
    abort_signal = getattr(context, 'abort_signal', None)
    
    if not block:
        if task.status not in ("running", "pending", "in_progress"):
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"<retrieval_status>success</retrieval_status>\n<task_id>{task.id}</task_id>\n<task_type>local_bash</task_type>\n<status>{task.status}</status>",
                is_error=False,
            )
        return ToolResult(
            tool_call_id=tool_call_id,
            output="<retrieval_status>not_ready</retrieval_status>",
            is_error=False,
        )
    
    result = await _wait_for_completion(task_id, session_id, timeout, abort_signal)
    retrieval_status = result["retrieval_status"]
    task_data = result["task"]
    
    output_parts = [f"<retrieval_status>{retrieval_status}</retrieval_status>"]
    if task_data:
        output_parts.append(f"<task_id>{task_data['id']}</task_id>")
        output_parts.append("<task_type>local_bash</task_type>")
        output_parts.append(f"<status>{task_data['status']}</status>")
        if task_data.get("output"):
            output_parts.append(f"<output>\n{task_data['output']}\n</output>")
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output="\n\n".join(output_parts),
        is_error=False,
    )


TaskOutputTool = ToolDef(
    name="task_output",
    description="Retrieve output from a running or completed background task",
    input_schema=INPUT_SCHEMA,
    is_read_only=True,
    risk_level="low",
    execute=_execute,
)


__all__ = ["TaskOutputTool"]