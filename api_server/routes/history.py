"""
FastAPI routes for History API.
提供會話歷史的完整管理，包括全文搜索和分頁。
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services.history import get_history_db, HistorySession, HistoryMessage, HistorySearchResult


router = APIRouter(prefix="/history", tags=["history"])


class HistorySessionCreate(BaseModel):
    user_id: str = "default"
    title: str = ""
    mode: str = "chat"
    folder: Optional[str] = None
    model: str = ""
    provider: str = ""


class HistorySessionUpdate(BaseModel):
    title: Optional[str] = None
    mode: Optional[str] = None
    folder: Optional[str] = None


class HistoryMessageCreate(BaseModel):
    session_id: str
    role: str
    content: str
    token_count: int = 0


class HistoryResponse(BaseModel):
    session: HistorySession
    messages: list[HistoryMessage]
    total_tokens: int


class HistoryListResponse(BaseModel):
    sessions: list[HistorySession]
    total: int
    limit: int
    offset: int


class HistorySearchResponse(BaseModel):
    results: list[HistorySearchResult]
    query: str


@router.post("/sessions", response_model=HistorySession)
async def create_history_session(data: HistorySessionCreate):
    session = HistorySession(
        id=str(uuid.uuid4()),
        user_id=data.user_id,
        title=data.title,
        mode=data.mode,
        folder=data.folder,
        model=data.model,
        provider=data.provider,
    )
    return get_history_db().create_session(session)


@router.get("/sessions", response_model=HistoryListResponse)
async def list_history_sessions(
    user_id: str = "default",
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    mode: Optional[str] = None,
):
    sessions = get_history_db().list_sessions(
        user_id=user_id,
        limit=limit,
        offset=offset,
        mode=mode,
    )
    total = get_history_db().count_sessions(user_id=user_id, mode=mode)
    return HistoryListResponse(
        sessions=sessions,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/sessions/{session_id}", response_model=HistoryResponse)
async def get_history_session(
    session_id: str,
    message_limit: int = Query(default=100, ge=1, le=1000),
    message_offset: int = Query(default=0, ge=0),
):
    session = get_history_db().get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = get_history_db().get_messages(
        session_id,
        limit=message_limit,
        offset=message_offset,
    )
    total_tokens = get_history_db().get_session_token_count(session_id)

    return HistoryResponse(
        session=session,
        messages=messages,
        total_tokens=total_tokens,
    )


@router.put("/sessions/{session_id}")
async def update_history_session(session_id: str, data: HistorySessionUpdate):
    session = get_history_db().get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    update_data = {}
    if data.title is not None:
        update_data["title"] = data.title
    if data.mode is not None:
        update_data["mode"] = data.mode
    if data.folder is not None:
        update_data["folder"] = data.folder

    if update_data:
        get_history_db().update_session(session_id, **update_data)

    return {"ok": True}


@router.delete("/sessions/{session_id}")
async def delete_history_session(session_id: str):
    success = get_history_db().delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.post("/messages", response_model=HistoryMessage)
async def add_history_message(data: HistoryMessageCreate):
    session = get_history_db().get_session(data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    message = HistoryMessage(
        session_id=data.session_id,
        role=data.role,
        content=data.content,
        token_count=data.token_count,
    )
    return get_history_db().add_message(message)


@router.get("/search", response_model=HistorySearchResponse)
async def search_history(
    q: str = Query(..., min_length=1),
    user_id: str = "default",
    limit: int = Query(default=20, ge=1, le=100),
):
    results = get_history_db().search(
        query=q,
        user_id=user_id,
        limit=limit,
    )
    return HistorySearchResponse(results=results, query=q)
