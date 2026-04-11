"""
FastAPI routes for session management.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator

router = APIRouter(prefix="/sessions", tags=["sessions"])

SESSIONS_DIR = Path.home() / ".claude" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class Message(BaseModel):
    role: str
    content: str | list


class SessionCreate(BaseModel):
    model: Optional[str] = None
    provider: Optional[str] = None


class SessionUpdate(BaseModel):
    title: str


class SessionSave(BaseModel):
    metadata: Optional[dict] = None


class SessionResponse(BaseModel):
    id: str
    title: Optional[str] = None
    model: str
    provider: str
    messageCount: int = 0
    createdAt: Optional[str] = None
    created_at: Optional[str] = None
    mode: str = "chat"
    folder: Optional[str] = None
    preview: str = ""
    messages: Optional[list[Message]] = None

    @validator("createdAt", "created_at", pre=True)
    def coerce_to_str(cls, v):
        if v is None:
            return v
        return str(v)


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class SessionStoredResponse(BaseModel):
    sessions: list[SessionResponse]


def _get_session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _load_session_file(session_id: str) -> Optional[dict]:
    path = _get_session_path(session_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _save_session_file(session_id: str, data: dict) -> None:
    path = _get_session_path(session_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _list_session_files() -> list[dict]:
    sessions = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
                if isinstance(data, dict) and "id" in data:
                    sessions.append(data)
        except Exception:
            continue
    return sessions


def _generate_preview(messages: list[dict]) -> str:
    try:
        first_user = next((m for m in messages if m.get("role") == "user"), None)
        if not first_user:
            return "(empty)"

        content = first_user.get("content", "")
        if isinstance(content, str):
            return content[:100]
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    return block.get("text", "")[:100]
        return "(media)"
    except Exception:
        return "(preview error)"


def _generate_title(messages: list[dict]) -> str:
    try:
        preview = _generate_preview(messages)
        if preview == "(empty)":
            return "New Chat"
        return preview[:50] + "..." if len(preview) > 50 else preview
    except Exception:
        return "New Chat"


_active_sessions: dict[str, dict] = {}


def _get_active_session(session_id: str) -> Optional[dict]:
    return _active_sessions.get(session_id)


def _get_all_active_sessions() -> list[dict]:
    return list(_active_sessions.values())


def _create_active_session(model: Optional[str] = None, provider: Optional[str] = None) -> dict:
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    session = {
        "id": session_id,
        "model": model or "claude-3-5-sonnet-20241022",
        "provider": provider or "anthropic",
        "messages": [],
        "createdAt": now,
        "title": None,
        "mode": "chat",
        "folder": None,
    }
    _active_sessions[session_id] = session
    return session


@router.get("", response_model=SessionListResponse)
async def list_sessions():
    try:
        stored_sessions = _list_session_files()
        result_sessions = []
        for s in stored_sessions:
            session_id = s.get("id")
            if not session_id:
                continue
            title = s.get("title")
            if not title:
                session_id_str = str(session_id)
                title = "Chat " + session_id_str[:8] + "..."
            resp = SessionResponse(
                id=session_id,
                title=title,
                model=str(s.get("model", "")),
                provider="",
                messageCount=0,
                created_at=str(s.get("updatedAt") or s.get("createdAt") or ""),
                mode=str(s.get("mode") or "chat"),
                folder=s.get("folder"),
                preview="",
            )
            result_sessions.append(resp)
        return SessionListResponse(sessions=result_sessions)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error: " + str(e))


@router.post("", response_model=SessionResponse)
async def create_session(data: Optional[SessionCreate] = None):
    model = data.model if data else None
    provider = data.provider if data else None
    session = _create_active_session(model=model, provider=provider)
    return SessionResponse(
        id=session["id"],
        model=session["model"],
        provider=session["provider"],
        messageCount=0,
        createdAt=session["createdAt"],
        preview="(new session)",
    )


@router.get("/stored/list", response_model=SessionStoredResponse)
async def list_stored_sessions(limit: Optional[int] = None):
    sessions = _list_session_files()
    if limit:
        sessions = sessions[:limit]
    return SessionStoredResponse(
        sessions=[
            SessionResponse(
                id=s["id"],
                title=s.get("title"),
                model=s.get("model", ""),
                provider="",
                messageCount=len(s.get("messages", [])),
                created_at=s.get("updatedAt") or s.get("createdAt", ""),
                mode=s.get("mode", "chat"),
                folder=s.get("folder"),
                preview="",
            )
            for s in sessions
            if s.get("id")
        ]
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    session = _get_active_session(session_id)
    if session:
        return SessionResponse(
            id=session["id"],
            model=session.get("model", ""),
            provider=session.get("provider", ""),
            messages=[Message(**m) if isinstance(m, dict) else m for m in session.get("messages", [])],
            createdAt=session.get("createdAt"),
        )

    stored = _load_session_file(session_id)
    if stored:
        return SessionResponse(
            id=stored["id"],
            title=stored.get("title"),
            model=stored.get("model", ""),
            provider=stored.get("provider", ""),
            messageCount=len(stored.get("messages", [])),
            createdAt=stored.get("createdAt"),
            mode=stored.get("mode", "chat"),
            folder=stored.get("folder"),
            preview=_generate_preview(stored.get("messages", [])),
        )

    raise HTTPException(status_code=404, detail="Session not found")


@router.put("/{session_id}")
async def update_session(session_id: str, data: SessionUpdate):
    if not data.title:
        raise HTTPException(status_code=400, detail="Missing or invalid title")

    session = _get_active_session(session_id)
    if session:
        session["title"] = data.title
        return {"ok": True, "id": session_id, "title": data.title}

    stored = _load_session_file(session_id)
    if stored:
        stored["title"] = data.title
        _save_session_file(session_id, stored)
        return {"ok": True, "id": session_id, "title": data.title}

    raise HTTPException(status_code=404, detail="Session not found")


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    path = _get_session_path(session_id)
    if path.exists():
        path.unlink()
    _active_sessions.pop(session_id, None)
    return {"ok": True}


@router.post("/{session_id}/save")
async def save_session(session_id: str, data: Optional[SessionSave] = None):
    session = _get_active_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found")

    metadata = data.metadata if data else None
    messages = session.get("messages", [])

    stored_data = {
        "id": session["id"],
        "title": _generate_title(messages),
        "mode": session.get("mode", "chat"),
        "folder": session.get("folder"),
        "model": session.get("model", ""),
        "provider": session.get("provider", ""),
        "messages": messages,
        "createdAt": session.get("createdAt"),
        "updatedAt": datetime.utcnow().isoformat(),
        "metadata": metadata,
    }

    _save_session_file(session_id, stored_data)
    return {"ok": True, "id": session_id}
