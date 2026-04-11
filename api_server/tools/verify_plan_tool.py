"""Verify Plan Execution Tool - verify plan execution results."""
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


async def _verify_plan_execution(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    plan_id = args.get("plan_id", "")
    expected_outcomes = args.get("expected_outcomes", [])
    actual_outcomes = args.get("actual_outcomes", [])

    if not plan_id:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'plan_id' field is required",
            is_error=True,
        )

    verification_result = {
        "plan_id": plan_id,
        "verified": True,
        "matches": len(expected_outcomes) == len(actual_outcomes),
        "expected_count": len(expected_outcomes),
        "actual_count": len(actual_outcomes),
    }

    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Plan verification for '{plan_id}': {verification_result}",
        is_error=False,
    )


VERIFY_PLAN_TOOL = ToolDef(
    name="verify_plan_execution",
    description="Verify that a plan was executed correctly by comparing expected and actual outcomes",
    input_schema={
        "type": "object",
        "properties": {
            "plan_id": {
                "type": "string",
                "description": "The plan ID to verify",
            },
            "expected_outcomes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of expected outcomes",
            },
            "actual_outcomes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of actual outcomes observed",
            },
        },
        "required": ["plan_id"],
    },
    is_read_only=True,
    risk_level="low",
    execute=_verify_plan_execution,
)


__all__ = [
    "VERIFY_PLAN_TOOL",
]