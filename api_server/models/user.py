from sqlalchemy import Column, String, Boolean, DateTime, Index
from api_server.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, SoftDeleteMixin
import datetime

class User(Base, TimestampMixin, UUIDPrimaryKeyMixin, SoftDeleteMixin):
    __tablename__ = "users"
    
    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    token_revoked_at = Column(DateTime, nullable=True, default=None)
    
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_username_active", "username", "is_active"),
    )