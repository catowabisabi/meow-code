"""
Schedule Cron Tool - Schedule recurring tasks with cron expressions.

This tool manages scheduled remote agent triggers, allowing users to create,
list, update, and delete scheduled tasks.
"""
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult
from .cron_tool import cron_create, cron_delete, cron_list


SCHEDULE_CRON_TOOL_NAME = "schedule_cron"


async def _schedule_cron_execute(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Execute schedule cron tool - manage scheduled tasks."""
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    action = args.get("action", "list")
    
    if action == "create":
        cron_expr = args.get("cron")
        prompt = args.get("prompt")
        recurring = args.get("recurring", True)
        durable = args.get("durable", False)
        
        if not cron_expr or not prompt:
            return ToolResult(
                tool_call_id=tool_call_id,
                output="Error: action 'create' requires 'cron' and 'prompt' parameters",
                is_error=True,
            )
        
        result = await cron_create(
            cron=cron_expr,
            prompt=prompt,
            recurring=recurring,
            durable=durable,
        )
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Created scheduled task: {result.get('id', 'unknown')}\nSchedule: {result.get('humanSchedule', cron_expr)}",
            is_error=False,
        )
    
    elif action == "delete":
        task_id = args.get("task_id")
        if not task_id:
            return ToolResult(
                tool_call_id=tool_call_id,
                output="Error: action 'delete' requires 'task_id' parameter",
                is_error=True,
            )
        
        result = await cron_delete(task_id)
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Deleted task: {task_id}" if result.get("success") else f"Failed to delete task: {task_id}",
            is_error=not result.get("success", False),
        )
    
    elif action == "list":
        tasks = await cron_list()
        
        if not tasks:
            return ToolResult(
                tool_call_id=tool_call_id,
                output="No scheduled tasks found",
                is_error=False,
            )
        
        task_lines = []
        for task in tasks:
            task_lines.append(
                f"- {task.get('id', 'unknown')}: {task.get('cron', '')} -> {task.get('prompt', '')[:50]}..."
            )
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Scheduled tasks:\n" + "\n".join(task_lines),
            is_error=False,
        )
    
    else:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Unknown action '{action}'. Must be one of: create, delete, list",
            is_error=True,
        )


SCHEDULE_CRON_TOOL = ToolDef(
    name=SCHEDULE_CRON_TOOL_NAME,
    description="Schedule recurring tasks with cron expressions. Use to schedule agents to run periodically.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "delete", "list"],
                "description": "The action to perform",
            },
            "cron": {
                "type": "string",
                "description": "Cron expression (e.g., '0 9 * * *' for daily at 9am)",
            },
            "prompt": {
                "type": "string",
                "description": "The prompt/command to execute when the task fires",
            },
            "task_id": {
                "type": "string",
                "description": "Task ID (required for delete action)",
            },
            "recurring": {
                "type": "boolean",
                "description": "Whether the task should repeat (default: True)",
            },
            "durable": {
                "type": "boolean",
                "description": "Whether the task should persist across restarts (default: False)",
            },
        },
        "required": ["action"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=_schedule_cron_execute,
)


__all__ = [
    "SCHEDULE_CRON_TOOL",
    "SCHEDULE_CRON_TOOL_NAME",
]
