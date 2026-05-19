from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from api_server.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Role(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "roles"
    
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(500), nullable=True)
    permissions = Column(String(2000), nullable=True)
    parent_id = Column(String(36), ForeignKey("roles.id"), nullable=True)
    
    parent = relationship("Role", remote_side="Role.id", backref="children", foreign_keys=[parent_id])
    
    __table_args__ = (
        Index("ix_roles_name_unique", "name", unique=True),
    )