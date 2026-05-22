from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from api_server.services.auth.token import TokenService
from api_server.db.repositories.user import UserRepository
from api_server.db.session import get_db_context

security = HTTPBearer(auto_error=False)


async def get_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    if not credentials:
        return None
    from api_server.core.config import settings
    token_service = TokenService(secret_key=settings.SECRET_KEY)
    payload = token_service.decode_token_unsafe(credentials.credentials)
    return payload


async def get_current_user(
    payload: Optional[dict] = Depends(get_token_payload),
) -> dict:
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    async with get_db_context() as db:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def require_admin(
    current_user: dict = Depends(get_current_active_user),
) -> dict:
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def optional_current_user(
    payload: Optional[dict] = Depends(get_token_payload),
) -> Optional[dict]:
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    async with get_db_context() as db:
        user_repo = UserRepository(db)
        return await user_repo.get_by_id(user_id)