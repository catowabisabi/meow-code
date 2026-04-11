"""Workflow Tool - execute predefined workflow sequences."""
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


WORKFLOW_STEPS = {
    "code_review": ["lint", "test", "review"],
    "deploy": ["build", "test", "deploy"],
    "debug": ["reproduce", "analyze", "fix", "verify"],
}


async def _workflow_execute(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    workflow_name = args.get("workflow", "")
    steps_override = args.get("steps", [])
    input_data = args.get("input", {})

    if not workflow_name:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'workflow' field is required",
            is_error=True,
        )

    steps = steps_override if steps_override else WORKFLOW_STEPS.get(workflow_name, [])

    if not steps:
        available = ", ".join(WORKFLOW_STEPS.keys())
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Unknown workflow '{workflow_name}'. Available: {available}",
            is_error=True,
        )

    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Workflow '{workflow_name}' executed with steps: {', '.join(steps)}. Input: {str(input_data)[:100]}",
        is_error=False,
    )


async def _workflow_list(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""

    workflows = []
    for name, steps in WORKFLOW_STEPS.items():
        workflows.append(f"  - {name}: {', '.join(steps)}")

    return ToolResult(
        tool_call_id=tool_call_id,
        output="Available workflows:\n" + "\n".join(workflows),
        is_error=False,
    )


WORKFLOW_EXECUTE_TOOL = ToolDef(
    name="workflow_execute",
    description="Execute a predefined workflow sequence",
    input_schema={
        "type": "object",
        "properties": {
            "workflow": {
                "type": "string",
                "description": "Name of the workflow to execute",
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: Override default steps for the workflow",
            },
            "input": {
                "type": "object",
                "description": "Input data for the workflow",
            },
        },
        "required": ["workflow"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=_workflow_execute,
)


WORKFLOW_LIST_TOOL = ToolDef(
    name="workflow_list",
    description="List all available predefined workflows",
    input_schema={
        "type": "object",
        "properties": {},
    },
    is_read_only=True,
    risk_level="low",
    execute=_workflow_list,
)


__all__ = [
    "WORKFLOW_EXECUTE_TOOL",
    "WORKFLOW_LIST_TOOL",
]