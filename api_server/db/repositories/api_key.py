"""API key repository."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_server.db.repositories.base import ApiKey, BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ApiKey, session)

    async def get_by_key(self, key: str) -> Optional[ApiKey]:
        result = await self._session.execute(
            select(ApiKey).where(ApiKey.key == key)
        )
        return result.scalars().first()

    async def get_by_user_id(self, user_id: str) -> List[ApiKey]:
        result = await self._session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_active_keys(self) -> List[ApiKey]:
        result = await self._session.execute(
            select(ApiKey).where(ApiKey.revoked.is_(False))
        )
        return list(result.scalars().all())

    async def revoke(self, id: str) -> bool:
        return await self.update(id, revoked=True, revoked_at=datetime.utcnow())