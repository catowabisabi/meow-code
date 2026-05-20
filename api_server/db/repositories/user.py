"""User repository with password helpers."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_server.db.repositories.base import BaseRepository
from api_server.models.user import User


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalars().first()

    async def get_by_provider(
        self, provider: str, provider_id: str
    ) -> Optional[User]:
        result = await self._session.execute(
            select(User).where(
                User.provider == provider,
                User.provider_id == provider_id
            )
        )
        return result.scalars().first()

    async def create_with_password(
        self,
        username: str,
        email: str,
        hashed_password: str,
        **kwargs,
    ) -> User:
        return await self.create(
            username=username,
            email=email,
            hashed_password=hashed_password,
            **kwargs
        )

    async def verify_password(
        self, username: str, hashed_password: str
    ) -> bool:
        user = await self.get_by_username(username)
        if user is None:
            return False
        return user.hashed_password == hashed_password