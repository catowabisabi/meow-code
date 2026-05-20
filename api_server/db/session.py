"""Async session factory and context managers."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


def get_db(session_factory: async_sessionmaker[AsyncSession] = Depends(lambda: get_session_factory(None))) -> AsyncSession:
    raise NotImplementedError("Use get_db_context instead")


@asynccontextmanager
async def get_db_context(
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
) -> AsyncGenerator[AsyncSession, None]:
    if session_factory is None:
        from api_server.db.database import _get_engine
        engine = _get_engine()
        session_factory = get_session_factory(engine)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_readonly_db(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        try:
            await session.execute(text("SELECT 1"))
            yield session
        finally:
            await session.close()