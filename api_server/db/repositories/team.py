"""Team repository with membership helpers."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_server.db.repositories.base import BaseRepository
from api_server.models.team import Team


class TeamRepository(BaseRepository[Team]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Team, session)

    async def get_by_department(self, department_id: str) -> List[Team]:
        result = await self._session.execute(
            select(Team).where(Team.department_id == department_id)
        )
        return list(result.scalars().all())

    async def get_by_leader(self, leader_id: str) -> List[Team]:
        result = await self._session.execute(
            select(Team).where(Team.leader_id == leader_id)
        )
        return list(result.scalars().all())

    async def get_by_name_and_department(
        self, name: str, department_id: Optional[str]
    ) -> Optional[Team]:
        query = select(Team).where(Team.name == name)
        if department_id:
            query = query.where(Team.department_id == department_id)
        result = await self._session.execute(query)
        return result.scalars().first()