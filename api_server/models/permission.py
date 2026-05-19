from sqlalchemy import Column, String, Index
from api_server.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Permission(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "permissions"
    
    name = Column(String(100), nullable=False, unique=True, index=True)
    resource = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    
    __table_args__ = (
        Index("ix_permissions_resource_action", "resource", "action"),
        Index("ix_permissions_name_unique", "name", unique=True),
    )