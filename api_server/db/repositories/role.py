"""Role repository."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_server.db.repositories.base import BaseRepository, Role


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Role, session)

    async def get_by_name(self, name: str) -> Optional[Role]:
        result = await self._session.execute(
            select(Role).where(Role.name == name)
        )
        return result.scalars().first()

    async def get_by_user_id(self, user_id: str) -> List[Role]:
        result = await self._session.execute(
            select(Role).where(Role.user_id == user_id)
        )
        return list(result.scalars().all())