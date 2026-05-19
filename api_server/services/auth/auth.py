from typing import Optional
from api_server.db.repositories.user import UserRepository
from api_server.services.auth.password import PasswordService
from api_server.services.auth.token import TokenService


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordService,
        token_service: TokenService,
    ):
        self.user_repo = user_repository
        self.password_service = password_service
        self.token_service = token_service

    async def register(
        self,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> dict:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")
        existing = await self.user_repo.get_by_username(username)
        if existing:
            raise ValueError("Username already taken")

        hashed = self.password_service.hash(password)
        user = await self.user_repo.create(
            email=email,
            username=username,
            hashed_password=hashed,
            full_name=full_name,
        )

        access_token = self.token_service.create_access_token(user.id)
        refresh_token = self.token_service.create_refresh_token(user.id)

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    async def login(self, username: str, password: str) -> dict:
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise ValueError("Invalid credentials")
        if not self.password_service.verify(user.hashed_password, password):
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("Account is disabled")

        access_token = self.token_service.create_access_token(user.id)
        refresh_token = self.token_service.create_refresh_token(user.id)

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    async def refresh(self, refresh_token: str) -> dict:
        payload = self.token_service.verify_token(refresh_token, expected_type="refresh")
        if not payload:
            raise ValueError("Invalid refresh token")

        user = await self.user_repo.get_by_id(payload.sub)
        if not user or not user.is_active:
            raise ValueError("User not found or disabled")

        access_token = self.token_service.create_access_token(user.id)
        new_refresh_token = self.token_service.create_refresh_token(user.id)

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        }

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        return await self.user_repo.get_by_id(user_id)

    async def verify_password(self, user_id: str, password: str) -> bool:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False
        return self.password_service.verify(user.hashed_password, password)

    async def update_password(self, user_id: str, new_password: str) -> None:
        hashed = self.password_service.hash(new_password)
        await self.user_repo.update(user_id, hashed_password=hashed)