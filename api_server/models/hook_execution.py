from sqlalchemy import Column, String, Text, Integer, ForeignKey, Index
from api_server.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class HookExecution(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "hook_executions"
    
    hook_id = Column(String(36), ForeignKey("hooks.id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    started_at = Column(String(50), nullable=True)
    completed_at = Column(String(50), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    
    __table_args__ = (
        Index("ix_hook_executions_hook_id", "hook_id"),
        Index("ix_hook_executions_status", "status"),
    )