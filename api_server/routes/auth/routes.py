from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from api_server.routes.auth.schemas import (
    RegisterRequest, LoginRequest, RefreshRequest,
    UpdatePasswordRequest, TokenResponse, MessageResponse, UserResponse,
)
from api_server.services.auth import AuthService
from api_server.db.session import get_db_context
from api_server.middleware.auth import get_current_active_user, get_token_payload
from sqlalchemy.ext.asyncio import AsyncSession

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_auth_service() -> AuthService:
    from api_server.services.auth import AuthService
    from api_server.services.auth.password import PasswordService
    from api_server.services.auth.token import TokenService
    from api_server.db.repositories.user import UserRepository
    from api_server.core.config import settings
    from api_server.db.database import _get_engine
    from api_server.db.session import get_session_factory
    
    engine = _get_engine()
    session_factory = get_session_factory(engine)
    
    async with session_factory() as db:
        user_repo = UserRepository(db)
        password_service = PasswordService()
        token_service = TokenService(
            secret_key=settings.SECRET_KEY,
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )
        return AuthService(user_repo, password_service, token_service)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    from api_server.services.auth.password import PasswordService
    from api_server.services.auth.token import TokenService
    from api_server.db.repositories.user import UserRepository
    from api_server.core.config import settings
    from api_server.db.database import _get_engine
    from api_server.db.session import get_session_factory
    
    engine = _get_engine()
    session_factory = get_session_factory(engine)
    
    async with session_factory() as db:
        try:
            user_repo = UserRepository(db)
            password_service = PasswordService()
            token_service = TokenService(
                secret_key=settings.SECRET_KEY,
                algorithm="HS256",
                access_token_expire_minutes=30,
                refresh_token_expire_days=7,
            )
            auth_service = AuthService(user_repo, password_service, token_service)
            
            result = await auth_service.register(
                email=request.email,
                username=request.username,
                password=request.password,
                full_name=request.full_name,
            )
            await db.commit()
            return TokenResponse(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                user=UserResponse.model_validate(result["user"]),
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    from api_server.services.auth.password import PasswordService
    from api_server.services.auth.token import TokenService
    from api_server.db.repositories.user import UserRepository
    from api_server.core.config import settings
    from api_server.db.database import _get_engine
    from api_server.db.session import get_session_factory
    
    engine = _get_engine()
    session_factory = get_session_factory(engine)
    
    async with session_factory() as db:
        try:
            user_repo = UserRepository(db)
            password_service = PasswordService()
            token_service = TokenService(
                secret_key=settings.SECRET_KEY,
                algorithm="HS256",
                access_token_expire_minutes=30,
                refresh_token_expire_days=7,
            )
            auth_service = AuthService(user_repo, password_service, token_service)
            
            result = await auth_service.login(request.username, request.password)
            await db.commit()
            return TokenResponse(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                user=UserResponse.model_validate(result["user"]),
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    from api_server.services.auth.password import PasswordService
    from api_server.services.auth.token import TokenService
    from api_server.db.repositories.user import UserRepository
    from api_server.core.config import settings
    from api_server.db.database import _get_engine
    from api_server.db.session import get_session_factory
    
    engine = _get_engine()
    session_factory = get_session_factory(engine)
    
    async with session_factory() as db:
        try:
            user_repo = UserRepository(db)
            password_service = PasswordService()
            token_service = TokenService(
                secret_key=settings.SECRET_KEY,
                algorithm="HS256",
                access_token_expire_minutes=30,
                refresh_token_expire_days=7,
            )
            auth_service = AuthService(user_repo, password_service, token_service)
            
            result = await auth_service.refresh(request.refresh_token)
            await db.commit()
            return TokenResponse(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                user=UserResponse.model_validate(result["user"]),
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: Optional[dict] = Depends(get_token_payload),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    if payload and credentials:
        user_id = payload.get("sub")
        if user_id:
            from api_server.db.repositories.user import UserRepository
            from api_server.db.database import _get_engine
            from api_server.db.session import get_session_factory
            from datetime import datetime, timezone
            
            engine = _get_engine()
            session_factory = get_session_factory(engine)
            async with session_factory() as db:
                user_repo = UserRepository(db)
                await user_repo.update(user_id, token_revoked_at=datetime.now(timezone.utc))
                await db.commit()
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_active_user)):
    return UserResponse.model_validate(current_user)