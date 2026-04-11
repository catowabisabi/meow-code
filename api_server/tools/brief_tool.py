"""
Brief Tool — send a message to the user.
This is the primary visible output channel.
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .types import ToolDef, ToolContext, ToolResult


async def _brief_execute(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Execute brief tool - sends a message to the user."""
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    message = args.get('message', '')
    attachments = args.get('attachments', [])
    status = args.get('status', 'normal')
    
    if not message and not attachments:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Brief requires a message or attachments",
            is_error=True,
        )
    
    result = {
        "message": message,
        "status": status,
        "sentAt": None,
    }
    
    # Resolve attachments if provided
    resolved_attachments = []
    if attachments:
        for att in attachments:
            att_path = Path(att)
            if att_path.exists():
                resolved_attachments.append({
                    "path": str(att_path),
                    "size": att_path.stat().st_size,
                    "isImage": att_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
                })
            else:
                resolved_attachments.append({
                    "path": str(att_path),
                    "size": 0,
                    "isImage": False,
                    "error": "File not found",
                })
        
        result["attachments"] = resolved_attachments
    
    # Format output for display
    output_parts = []
    if message:
        output_parts.append(message)
    
    if attachments:
        att_count = len(attachments)
        output_parts.append(f"({att_count} attachment{'s' if att_count > 1 else ''} sent)")
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output="\n".join(output_parts),
        is_error=False,
        # Store full result in metadata for UI
    )


BRIEF_TOOL = ToolDef(
    name="brief",
    description="Send a message to the user — your primary visible output channel. Use for task completion notifications, status updates, or any message you want the user to see.",
    input_schema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message for the user. Supports markdown formatting.",
            },
            "attachments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional file paths to attach (photos, screenshots, diffs, logs).",
            },
            "status": {
                "type": "string",
                "enum": ["normal", "proactive"],
                "description": "'proactive' for unsolicited updates, 'normal' for replies.",
            },
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=_brief_execute,
)


__all__ = ["BRIEF_TOOL"]
