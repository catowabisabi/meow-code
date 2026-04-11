"""
FastAPI routes for session export.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/sessions", tags=["export"])

SESSIONS_DIR = Path.home() / ".claude" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class ExportResponse(BaseModel):
    content: str
    filename: str
    message_count: int


def _get_session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _load_session_file(session_id: str) -> Optional[dict]:
    path = _get_session_path(session_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return __import__("json").load(f)
    except Exception:
        return None


def _format_timestamp(date: datetime) -> str:
    year = date.year
    month = str(date.month).zfill(2)
    day = str(date.day).zfill(2)
    hours = str(date.hour).zfill(2)
    minutes = str(date.minute).zfill(2)
    seconds = str(date.second).zfill(2)
    return f"{year}-{month}-{day}-{hours}{minutes}{seconds}"


def _extract_first_prompt(messages: list[dict]) -> str:
    first_user = next((m for m in messages if m.get("role") == "user"), None)
    if not first_user:
        return ""
    
    content = first_user.get("content", "")
    result = ""
    if isinstance(content, str):
        result = content.strip()
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                result = block.get("text", "").strip()
                break
    
    result = result.split('\n')[0] or ''
    if len(result) > 50:
        result = result[:49] + '…'
    return result


def _sanitize_filename(text: str) -> str:
    result = text.lower()
    result = "".join(c if c.isalnum() or c.isspace() or c == '-' else '' for c in result)
    result = "-".join(result.split())
    result = result.replace('-+', '-')
    result = result.strip('-')
    return result


def _format_message_content(content: Union[str, List]) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    parts.append(f"[Tool: {block.get('name', 'unknown')}]")
                elif block.get("type") == "tool_result":
                    parts.append("[Tool Result]")
        return "\n".join(parts)
    return str(content)


def _render_messages_to_plain_text(messages: list[dict]) -> str:
    """Render messages as plain text conversation."""
    lines = ["# Conversation", ""]
    
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        timestamp = ""
        if "timestamp" in msg:
            timestamp = f"[{msg['timestamp']}] "
        elif "created_at" in msg:
            timestamp = f"[{msg['created_at']}] "
        
        formatted_content = _format_message_content(content)
        
        if role == "user":
            lines.append(f"{timestamp}User: {formatted_content}")
        elif role == "assistant":
            lines.append(f"{timestamp}Assistant: {formatted_content}")
        else:
            lines.append(f"{timestamp}{role.capitalize()}: {formatted_content}")
        
        lines.append("")
    
    return "\n".join(lines).strip()


_active_sessions: dict[str, dict] = {}


def _get_active_session(session_id: str) -> Optional[dict]:
    return _active_sessions.get(session_id)


@router.post("/{session_id}/export", response_model=ExportResponse)
async def export_session(session_id: str, format: str = "text"):
    """
    Export a session conversation as text.
    
    Args:
        session_id: The session ID to export
        format: Export format - "text" (default) or "markdown"
    
    Returns:
        ExportResponse with content, filename, and message count
    """
    if format not in ("text", "markdown"):
        raise HTTPException(status_code=400, detail="Format must be 'text' or 'markdown'")
    
    session = _get_active_session(session_id)
    
    if not session:
        stored = _load_session_file(session_id)
        if stored:
            session = stored
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = session.get("messages", [])
    message_count = len(messages)
    
    content = _render_messages_to_plain_text(messages)
    
    timestamp = _format_timestamp(datetime.now())
    first_prompt = _extract_first_prompt(messages)
    
    if first_prompt:
        sanitized = _sanitize_filename(first_prompt)
        if sanitized:
            filename = f"{timestamp}-{sanitized}.txt"
        else:
            filename = f"conversation-{timestamp}.txt"
    else:
        filename = f"conversation-{timestamp}.txt"
    
    return ExportResponse(
        content=content,
        filename=filename,
        message_count=message_count
    )