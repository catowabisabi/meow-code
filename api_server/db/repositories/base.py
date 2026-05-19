"""Base repository with generic CRUD operations."""
from __future__ import annotations

from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_server.models.base import Base

T = TypeVar("T", bound=Base)


class Role(Base):
    pass


class ApiKey(Base):
    pass


class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def get_by_id(self, id: str) -> Optional[T]:
        return await self._session.get(self._model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        result = await self._session.execute(
            select(self._model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._session.execute(
            select(self._model)
        )
        return len(list(result.scalars().all()))

    async def create(self, **kwargs: Any) -> T:
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(self, id: str, **kwargs: Any) -> Optional[T]:
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, id: str) -> bool:
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True

    async def exists(self, id: str) -> bool:
        instance = await self.get_by_id(id)
        return instance is not None