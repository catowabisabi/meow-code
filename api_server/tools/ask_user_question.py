"""
Ask User Question Tool — ask the user a question and wait for their response.
"""
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


async def execute_ask_user_question(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """
    Execute ask_user_question tool.
    
    Asks the user a question and blocks until their response.
    """
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    question = args.get('question', '')
    options = args.get('options', None)
    timeout = args.get('timeout', 300)
    
    if not question:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="No question provided",
            is_error=True,
        )
    
    output_parts = [f"Question: {question}"]
    
    if options and len(options) > 0:
        output_parts.append("\nOptions:")
        for i, opt in enumerate(options, 1):
            output_parts.append(f"  {i}. {opt}")
    
    output_parts.append(f"\n(Timeout: {timeout}s - awaiting user response...)")
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output="\n".join(output_parts),
        is_error=False,
    )


TOOL_ASK_USER_QUESTION = ToolDef(
    name="ask_user_question",
    description="Ask the user a question and wait for their response",
    input_schema={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question to ask"},
            "options": {"type": "array", "items": {"type": "string"}, "description": "Optional choices"},
            "timeout": {"type": "number", "default": 300},
        },
        "required": ["question"]
    },
    is_read_only=True,
    risk_level="low",
    execute=execute_ask_user_question,
)


__all__ = ["TOOL_ASK_USER_QUESTION"]