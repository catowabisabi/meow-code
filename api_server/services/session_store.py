"""
Session Persistence Service.
Stores chat sessions as JSON files in ~/.claude/sessions/.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel


class ContentBlock(BaseModel):
    type: str
    text: Optional[str] = None
    source: Optional[dict] = None
    data: Optional[str] = None
    media_type: Optional[str] = None


class Message(BaseModel):
    role: str
    content: str | List[ContentBlock | dict]


class SessionSummary(BaseModel):
    id: str
    title: str
    mode: str
    folder: Optional[str]
    model: str
    updatedAt: int


class Session(BaseModel):
    id: str
    title: str
    mode: str
    folder: Optional[str]
    model: str
    provider: str
    messages: List[Message]
    createdAt: int
    updatedAt: int
    metadata: Optional[dict] = None


def _get_sessions_dir() -> Path:
    return Path.home() / ".claude" / "sessions"


def _get_session_path(session_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", session_id)
    return _get_sessions_dir() / f"{safe_id}.json"


async def _ensure_sessions_dir() -> None:
    sessions_dir = _get_sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)


def generate_title(messages: List[Message]) -> str:
    first_user = next((m for m in messages if m.role == "user"), None)
    if not first_user:
        return "Untitled Session"

    user_text = ""
    if isinstance(first_user.content, str):
        user_text = first_user.content
    elif isinstance(first_user.content, list):
        for block in first_user.content:
            if isinstance(block, dict) and block.get("type") == "text":
                user_text = block.get("text", "")
                break
            elif hasattr(block, "type") and block.type == "text":
                user_text = block.text
                break

    if not user_text:
        return "新的對話"
    
    trimmed = re.sub(r"\s+", " ", user_text).strip()
    if not trimmed:
        return "新的對話"
    
    if len(trimmed) <= 20:
        return trimmed
    
    near_boundary = trimmed[:20]
    last_space = near_boundary.rfind(" ")
    if last_space > 10:
        return trimmed[:last_space] + "..."
    
    return trimmed[:17] + "..."


class SessionStore:
    @staticmethod
    async def save_session(session: Session) -> None:
        await _ensure_sessions_dir()
        
        if not session.title:
            session.title = generate_title(session.messages)
        
        session.updatedAt = int(datetime.utcnow().timestamp() * 1000)
        
        file_path = _get_session_path(session.id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(), f, ensure_ascii=False, indent=2)
    
    @staticmethod
    async def load_session(session_id: str) -> Optional[Session]:
        file_path = _get_session_path(session_id)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Session(**data)
        except (json.JSONDecodeError, OSError):
            return None
    
    @staticmethod
    async def list_sessions(limit: Optional[int] = None) -> List[SessionSummary]:
        await _ensure_sessions_dir()
        
        dir_path = _get_sessions_dir()
        summaries: List[SessionSummary] = []
        
        try:
            entries = list(dir_path.glob("*.json"))
        except OSError:
            return []
        
        for entry in entries:
            try:
                with open(entry, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                
                if not session_data.get("id") or not session_data.get("messages"):
                    continue
                if not isinstance(session_data["messages"], list):
                    continue
                
                summaries.append(SessionSummary(
                    id=session_data["id"],
                    title=session_data.get("title", ""),
                    mode=session_data.get("mode", "chat"),
                    folder=session_data.get("folder"),
                    model=session_data.get("model", ""),
                    updatedAt=session_data.get("updatedAt", 0),
                ))
            except (json.JSONDecodeError, OSError):
                continue
        
        summaries.sort(key=lambda s: s.updatedAt, reverse=True)
        
        if limit and limit > 0:
            return summaries[:limit]
        
        return summaries
    
    @staticmethod
    async def delete_session(session_id: str) -> None:
        file_path = _get_session_path(session_id)
        try:
            file_path.unlink()
        except OSError:
            pass
