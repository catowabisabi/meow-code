"""
Ask User Question Tool — prompts the user with a multiple-choice question.
Blocks until the user answers.
"""
from typing import Any, Dict, List, Optional

from .types import ToolDef, ToolContext, ToolResult


async def _ask_user_execute(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """
    Execute ask user question tool.
    
    This is a blocking tool that waits for user input.
    In a real implementation, this would send a question to the UI
    and wait for the user's response via a future/await mechanism.
    """
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    questions = args.get('questions', [])
    answers = args.get('answers', {})
    annotations = args.get('annotations', {})
    
    if not questions:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="No questions provided",
            is_error=True,
        )
    
    # Format questions for display
    question_texts = []
    for q in questions:
        header = q.get('header', 'Question')
        question_text = q.get('question', '')
        options = q.get('options', [])
        
        option_texts = []
        for opt in options:
            label = opt.get('label', '')
            description = opt.get('description', '')
            option_texts.append(f"  - {label}: {description}" if description else f"  - {label}")
        
        question_texts.append(
            f"[{header}] {question_text}\n" + "\n".join(option_texts)
        )
    
    # Check if we already have answers (user responded)
    if answers:
        # Format the answers
        answer_parts = []
        for q_text, answer in answers.items():
            answer_parts.append(f'"{q_text}" = "{answer}"')
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"User answered: {', '.join(answer_parts)}",
            is_error=False,
        )
    
    # No answers yet - this is the initial call
    # In a real implementation, we would:
    # 1. Send the questions to the UI via WebSocket
    # 2. Wait for user response via a future
    # 3. Return the answers when received
    
    # For now, return the questions for display
    formatted_questions = "\n\n".join(question_texts)
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Questions for user:\n\n{formatted_questions}\n\n(Awaiting user response...)",
        is_error=False,
    )


ASK_USER_TOOL = ToolDef(
    name="ask_user",
    description="Ask the user a multiple-choice question. Pauses execution until the user answers. Use when you need user input to proceed.",
    input_schema={
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The complete question to ask the user.",
                        },
                        "header": {
                            "type": "string",
                            "description": "Short label displayed as a chip (max 20 chars).",
                        },
                        "options": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {
                                        "type": "string",
                                        "description": "Display text for this option (1-5 words).",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Explanation of what this option means.",
                                    },
                                },
                            },
                        },
                        "multiSelect": {
                            "type": "boolean",
                            "description": "Allow multiple selections (default: false).",
                        },
                    },
                    "required": ["question", "header", "options"],
                },
            },
            "answers": {
                "type": "object",
                "description": "User answers (filled by the system after user responds).",
            },
            "annotations": {
                "type": "object",
                "description": "Optional per-question annotations from user.",
            },
        },
        "required": ["questions"],
    },
    is_read_only=True,
    risk_level="low",
    execute=_ask_user_execute,
)


__all__ = ["ASK_USER_TOOL"]
