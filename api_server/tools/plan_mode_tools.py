"""Plan mode tools - enter/exit plan mode."""
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


plan_mode_active = False


async def _enter_plan_mode(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    global plan_mode_active
    
    reason = args.get('reason', 'Planning required')
    plan_mode_active = True
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Entered plan mode. Reason: {reason}",
        is_error=False,
    )


async def _exit_plan_mode(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    global plan_mode_active
    
    approved = args.get('approved', True)
    feedback = args.get('feedback', '')
    
    plan_mode_active = False
    
    if approved:
        output = "Exited plan mode - plan approved"
    else:
        output = f"Exited plan mode - plan rejected: {feedback}"
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=output,
        is_error=False,
    )


ENTER_PLAN_MODE_TOOL = ToolDef(
    name="enter_plan_mode",
    description="Enter plan mode to analyze a task and create a step-by-step plan before execution.",
    input_schema={
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Why plan mode is needed"},
            "task": {"type": "string", "description": "Task to plan for"},
        },
    },
    is_read_only=False,
    risk_level="medium",
    execute=_enter_plan_mode,
)


EXIT_PLAN_MODE_TOOL = ToolDef(
    name="exit_plan_mode",
    description="Exit plan mode and either approve or reject the plan.",
    input_schema={
        "type": "object",
        "properties": {
            "approved": {"type": "boolean", "description": "Whether the plan is approved"},
            "feedback": {"type": "string", "description": "Feedback if plan is rejected"},
        },
    },
    is_read_only=False,
    risk_level="medium",
    execute=_exit_plan_mode,
)


__all__ = ["ENTER_PLAN_MODE_TOOL", "EXIT_PLAN_MODE_TOOL"]
