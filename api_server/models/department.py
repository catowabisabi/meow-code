from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from api_server.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Department(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "departments"
    
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    parent_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    
    parent = relationship("Department", remote_side="Department.id", backref="children", foreign_keys=[parent_id])
    
    __table_args__ = (
        Index("ix_departments_name_unique", "name", unique=True),
    )