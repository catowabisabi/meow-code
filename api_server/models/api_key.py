from sqlalchemy import Column, String, DateTime, Boolean, Index, ForeignKey
from datetime import datetime
from api_server.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class ApiKey(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "api_keys"
    
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    prefix = Column(String(20), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_key_hash_unique", "key_hash", unique=True),
    )