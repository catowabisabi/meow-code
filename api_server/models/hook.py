from sqlalchemy import Column, String, Text, Boolean, JSON, Index, ForeignKey
from api_server.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Hook(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "hooks"
    
    name = Column(String(100), nullable=False, index=True)
    trigger_type = Column(String(50), nullable=False, index=True)
    hook_type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=True)
    code = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    __table_args__ = (
        Index("ix_hooks_trigger_type", "trigger_type"),
        Index("ix_hooks_user_id", "user_id"),
    )