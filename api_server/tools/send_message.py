"""
SendMessageTool - Send messages to teammates or broadcast to team.

Provides:
- Direct messaging to teammates
- Broadcast to all team members
- Shutdown request/response handling
- Plan approval/rejection

Based on the TypeScript SendMessageTool implementation in _claude_code_leaked_source_code.
"""
import json
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from .types import ToolDef, ToolContext, ToolResult


TOOL_NAME = "send_message"


@dataclass
class MessageRouting:
    sender: str
    sender_color: Optional[str] = None
    target: str = ""
    target_color: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None


_teammate_mailboxes: dict[str, list[dict]] = {}
_team_members: list[str] = []


async def _send_message(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    to = args.get("to", "")
    message = args.get("message", "")
    summary = args.get("summary")
    
    if not to:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'to' field is required",
            is_error=True,
        )
    
    if not message:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'message' field is required",
            is_error=True,
        )
    
    if isinstance(message, dict):
        return await _handle_structured_message(to, message, ctx, tool_call_id)
    
    routing = MessageRouting(
        sender="main",
        target=f"@{to}",
        summary=summary,
        content=message,
    )
    
    if to not in _teammate_mailboxes:
        _teammate_mailboxes[to] = []
    
    _teammate_mailboxes[to].append({
        "from": routing.sender,
        "text": message,
        "summary": summary,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "color": routing.sender_color,
    })
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=json.dumps({
            "success": True,
            "message": f"Message sent to {to}'s inbox",
            "routing": {
                "sender": routing.sender,
                "target": routing.target,
                "summary": routing.summary,
                "content": routing.content,
            },
        }),
        is_error=False,
    )


async def _handle_structured_message(
    to: str,
    message: dict,
    ctx: ToolContext,
    tool_call_id: str,
) -> ToolResult:
    msg_type = message.get("type", "")
    
    if msg_type == "shutdown_request":
        return await _handle_shutdown_request(to, message, tool_call_id)
    elif msg_type == "shutdown_response":
        return await _handle_shutdown_response(message, tool_call_id)
    elif msg_type == "plan_approval_response":
        return await _handle_plan_response(to, message, tool_call_id)
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Unknown message type: {msg_type}",
        is_error=True,
    )


async def _handle_shutdown_request(
    target: str,
    message: dict,
    tool_call_id: str,
) -> ToolResult:
    request_id = str(uuid.uuid4())
    reason = message.get("reason")
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=json.dumps({
            "success": True,
            "message": f"Shutdown request sent to {target}. Request ID: {request_id}",
            "request_id": request_id,
            "target": target,
        }),
        is_error=False,
    )


async def _handle_shutdown_response(
    message: dict,
    tool_call_id: str,
) -> ToolResult:
    request_id = message.get("request_id", "")
    approve = message.get("approve", False)
    reason = message.get("reason")
    
    if not approve and not reason:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: reason is required when rejecting a shutdown request",
            is_error=True,
        )
    
    if approve:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "message": "Shutdown approved",
                "request_id": request_id,
            }),
            is_error=False,
        )
    else:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "message": f"Shutdown rejected. Reason: {reason}",
                "request_id": request_id,
            }),
            is_error=False,
        )


async def _handle_plan_response(
    target: str,
    message: dict,
    tool_call_id: str,
) -> ToolResult:
    request_id = message.get("request_id", "")
    approve = message.get("approve", False)
    feedback = message.get("feedback")
    
    if approve:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "message": f"Plan approved for {target}",
                "request_id": request_id,
            }),
            is_error=False,
        )
    else:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "message": f"Plan rejected for {target}: {feedback or 'No feedback provided'}",
                "request_id": request_id,
            }),
            is_error=False,
        )


async def _broadcast_message(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    message = args.get("message", "")
    summary = args.get("summary")
    
    if not message:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: message is required",
            is_error=True,
        )
    
    recipients = [m for m in _team_members if m != "main"]
    
    if not recipients:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "success": True,
                "message": "No teammates to broadcast to (you are the only team member)",
                "recipients": [],
            }),
            is_error=False,
        )
    
    for recipient in recipients:
        if recipient not in _teammate_mailboxes:
            _teammate_mailboxes[recipient] = []
        
        _teammate_mailboxes[recipient].append({
            "from": "main",
            "text": message,
            "summary": summary,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=json.dumps({
            "success": True,
            "message": f"Message broadcast to {len(recipients)} teammate(s): {', '.join(recipients)}",
            "recipients": recipients,
        }),
        is_error=False,
    )


SEND_MESSAGE_TOOL = ToolDef(
    name=TOOL_NAME,
    description="Send a message to a specific teammate or broadcast to all teammates",
    input_schema={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient: teammate name, '*' for broadcast to all teammates",
            },
            "message": {
                "oneOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["shutdown_request", "shutdown_response", "plan_approval_response"],
                            },
                            "request_id": {"type": "string"},
                            "approve": {"type": "boolean"},
                            "reason": {"type": "string"},
                            "feedback": {"type": "string"},
                        },
                    },
                ],
                "description": "Plain text message content or structured message",
            },
            "summary": {
                "type": "string",
                "description": "A 5-10 word summary shown as a preview in the UI",
            },
        },
        "required": ["to", "message"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=_send_message,
)


BROADCAST_MESSAGE_TOOL = ToolDef(
    name="broadcast_message",
    description="Broadcast a message to all teammates in the team",
    input_schema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Plain text message content to broadcast",
            },
            "summary": {
                "type": "string",
                "description": "A 5-10 word summary shown as a preview in the UI",
            },
        },
        "required": ["message"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=_broadcast_message,
)


def get_mailbox(teammate_name: str) -> list[dict]:
    return _teammate_mailboxes.get(teammate_name, [])


def clear_mailbox(teammate_name: str) -> None:
    _teammate_mailboxes.pop(teammate_name, None)


def set_team_members(members: list[str]) -> None:
    global _team_members
    _team_members = members


__all__ = [
    "SEND_MESSAGE_TOOL",
    "BROADCAST_MESSAGE_TOOL",
    "get_mailbox",
    "clear_mailbox",
    "set_team_members",
]
