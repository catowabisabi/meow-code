"""Department repository with hierarchical helpers."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_server.db.repositories.base import BaseRepository
from api_server.models.department import Department


class DepartmentRepository(BaseRepository[Department]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Department, session)

    async def get_all_with_children(self, skip: int = 0, limit: int = 100) -> List[Department]:
        result = await self._session.execute(
            select(Department)
            .options(selectinload(Department.children))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Optional[Department]:
        result = await self._session.execute(
            select(Department).where(Department.name == name)
        )
        return result.scalars().first()

    async def get_children(self, parent_id: str) -> List[Department]:
        result = await self._session.execute(
            select(Department).where(Department.parent_id == parent_id)
        )
        return list(result.scalars().all())

    async def get_with_parent(self, department_id: str) -> Optional[Department]:
        result = await self._session.execute(
            select(Department)
            .options(selectinload(Department.parent))
            .where(Department.id == department_id)
        )
        return result.scalars().first()