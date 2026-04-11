"""Session models for chat session management."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from .message import Message


@dataclass
class Session:
    id: str
    model: str
    provider: str
    mode: str = "chat"
    folder: Optional[str] = None
    title: str = ""
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def model_dump(self, **kwargs) -> dict:
        return {
            "id": self.id,
            "model": self.model,
            "provider": self.provider,
            "mode": self.mode,
            "folder": self.folder,
            "title": self.title,
            "messages": [m.model_dump() if hasattr(m, 'model_dump') else m for m in self.messages],
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        messages = data.get("messages", [])
        messages = [Message.from_dict(m) if isinstance(m, dict) else m for m in messages]
        
        created_at = data.get("created_at", data.get("createdAt", datetime.now()))
        updated_at = data.get("updated_at", data.get("updatedAt", datetime.now()))
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        
        return cls(
            id=data.get("id", ""),
            model=data.get("model", ""),
            provider=data.get("provider", ""),
            mode=data.get("mode", "chat"),
            folder=data.get("folder"),
            title=data.get("title", ""),
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata", {})
        )


@dataclass
class SessionSummary:
    id: str
    title: str
    model: str
    provider: str
    mode: str
    folder: Optional[str]
    message_count: int
    created_at: str
    preview: str

    def model_dump(self, **kwargs) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "model": self.model,
            "provider": self.provider,
            "mode": self.mode,
            "folder": self.folder,
            "messageCount": self.message_count,
            "createdAt": self.created_at,
            "preview": self.preview
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionSummary":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            model=data.get("model", ""),
            provider=data.get("provider", ""),
            mode=data.get("mode", "chat"),
            folder=data.get("folder"),
            message_count=data.get("messageCount", data.get("message_count", 0)),
            created_at=data.get("createdAt", data.get("created_at", "")),
            preview=data.get("preview", "")
        )

    @classmethod
    def from_session(cls, session: Session, preview: str = "") -> "SessionSummary":
        return cls(
            id=session.id,
            title=session.title or "New Chat",
            model=session.model,
            provider=session.provider,
            mode=session.mode,
            folder=session.folder,
            message_count=len(session.messages),
            created_at=session.created_at.isoformat() if isinstance(session.created_at, datetime) else session.created_at,
            preview=preview
        )
