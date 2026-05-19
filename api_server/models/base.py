"""SQLAlchemy base models and mixins for the API server."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TimestampMixin:
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class UUIDPrimaryKeyMixin:
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False,
    )


class SoftDeleteMixin:
    deleted_at = Column(
        DateTime,
        nullable=True,
        default=None,
    )