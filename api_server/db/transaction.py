"""Transaction utilities for async database operations."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transaction(
    session: AsyncSession,
) -> AsyncGenerator[AsyncSession, None]:
    async with session.begin():
        yield session


@asynccontextmanager
async def savepoint(
    session: AsyncSession,
) -> AsyncGenerator[AsyncSession, None]:
    async with session.begin_nested():
        yield session