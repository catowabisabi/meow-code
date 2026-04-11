from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel


class Notification(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str
    createdAt: int
    read: bool = False
    source: Optional[str] = None
    data: Dict[str, Any] = {}


class NotifierService:
    _notifications: List[Notification] = []
    _max_notifications: int = 100
    _enabled: bool = True
    
    @classmethod
    async def send_notification(
        cls,
        title: str,
        message: str,
        notification_type: str = "info",
        source: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        notification = Notification(
            id=f"notif_{datetime.utcnow().timestamp()}",
            title=title,
            message=message,
            notification_type=notification_type,
            createdAt=int(datetime.utcnow().timestamp() * 1000),
            source=source,
            data=data or {},
        )
        cls._notifications.append(notification)
        
        if len(cls._notifications) > cls._max_notifications:
            cls._notifications = cls._notifications[-cls._max_notifications:]
        
        return notification
    
    @classmethod
    async def send_error(cls, title: str, message: str, source: Optional[str] = None) -> Notification:
        return await cls.send_notification(title, message, "error", source)
    
    @classmethod
    async def send_warning(cls, title: str, message: str, source: Optional[str] = None) -> Notification:
        return await cls.send_notification(title, message, "warning", source)
    
    @classmethod
    async def send_success(cls, title: str, message: str, source: Optional[str] = None) -> Notification:
        return await cls.send_notification(title, message, "success", source)
    
    @classmethod
    async def get_notifications(cls, unread_only: bool = False) -> List[Notification]:
        if unread_only:
            return [n for n in cls._notifications if not n.read]
        return cls._notifications
    
    @classmethod
    async def mark_as_read(cls, notification_id: str) -> bool:
        for n in cls._notifications:
            if n.id == notification_id:
                n.read = True
                return True
        return False
    
    @classmethod
    async def mark_all_as_read(cls) -> None:
        for n in cls._notifications:
            n.read = True
    
    @classmethod
    async def delete_notification(cls, notification_id: str) -> bool:
        for i, n in enumerate(cls._notifications):
            if n.id == notification_id:
                cls._notifications.pop(i)
                return True
        return False
    
    @classmethod
    async def clear_all(cls) -> None:
        cls._notifications.clear()
    
    @classmethod
    async def get_unread_count(cls) -> int:
        return len([n for n in cls._notifications if not n.read])
    
    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        cls._enabled = enabled
    
    @classmethod
    def is_enabled(cls) -> bool:
        return cls._enabled