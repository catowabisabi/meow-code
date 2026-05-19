from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from api_server.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Team(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "teams"
    
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    leader_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    __table_args__ = (
        Index("ix_teams_name_department", "name", "department_id"),
    )