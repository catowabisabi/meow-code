import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel


class ReplayEvent(BaseModel):
    timestamp: float
    event_type: str
    data: Dict[str, Any]


class VCRSession(BaseModel):
    session_id: str
    events: List[ReplayEvent]
    created_at: float
    duration_ms: int
    metadata: Dict[str, Any] = {}


class VCRService:
    _sessions: Dict[str, VCRSession] = {}
    
    @classmethod
    def _get_sessions_dir(cls) -> Path:
        d = Path.home() / ".claude" / "vcr_sessions"
        d.mkdir(parents=True, exist_ok=True)
        return d
    
    @classmethod
    async def start_recording(cls, session_id: str) -> bool:
        if session_id in cls._sessions:
            return False
        
        session = VCRSession(
            session_id=session_id,
            events=[],
            created_at=datetime.utcnow().timestamp(),
            duration_ms=0,
        )
        cls._sessions[session_id] = session
        return True
    
    @classmethod
    async def record_event(
        cls,
        session_id: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> bool:
        if session_id not in cls._sessions:
            return False
        
        event = ReplayEvent(
            timestamp=datetime.utcnow().timestamp(),
            event_type=event_type,
            data=data,
        )
        cls._sessions[session_id].events.append(event)
        return True
    
    @classmethod
    async def stop_recording(cls, session_id: str) -> Optional[VCRSession]:
        if session_id not in cls._sessions:
            return None
        
        session = cls._sessions[session_id]
        if session.events:
            first_ts = session.events[0].timestamp
            last_ts = session.events[-1].timestamp
            session.duration_ms = int((last_ts - first_ts) * 1000)
        
        await cls._persist_session(session)
        return session
    
    @classmethod
    async def get_session(cls, session_id: str) -> Optional[VCRSession]:
        if session_id in cls._sessions:
            return cls._sessions[session_id]
        
        path = cls._get_sessions_dir() / f"{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                session = VCRSession(**data)
                cls._sessions[session_id] = session
                return session
            except (json.JSONDecodeError, OSError):
                pass
        return None
    
    @classmethod
    async def list_sessions(cls) -> List[str]:
        dir_path = cls._get_sessions_dir()
        try:
            return [p.stem for p in dir_path.glob("*.json")]
        except OSError:
            return []
    
    @classmethod
    async def delete_session(cls, session_id: str) -> bool:
        if session_id in cls._sessions:
            del cls._sessions[session_id]
        
        path = cls._get_sessions_dir() / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
    
    @classmethod
    async def _persist_session(cls, session: VCRSession) -> None:
        path = cls._get_sessions_dir() / f"{session.session_id}.json"
        data = session.model_dump()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    @classmethod
    async def replay_session(
        cls,
        session_id: str,
        event_filter: Optional[List[str]] = None,
    ) -> List[ReplayEvent]:
        session = await cls.get_session(session_id)
        if not session:
            return []
        
        events = session.events
        if event_filter:
            events = [e for e in events if e.event_type in event_filter]
        
        return events