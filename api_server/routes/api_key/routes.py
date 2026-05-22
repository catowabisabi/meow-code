from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
from api_server.services.api_key import ApiKeyService
from api_server.db.repositories.api_key import ApiKeyRepository
from api_server.db.session import get_db_context
from api_server.middleware.auth import get_current_active_user

router = APIRouter(prefix="/api-keys", tags=["api_keys"])


class ApiKeyCreateRequest(BaseModel):
    name: str
    expires_in_days: int = 365


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    created_at: str
    expires_at: str | None
    last_used_at: str | None
    is_active: bool


class ApiKeyWithFullKeyResponse(BaseModel):
    id: str
    name: str
    full_key: str
    prefix: str
    created_at: str
    expires_at: str | None
    last_used_at: str | None
    is_active: bool


async def get_api_key_service() -> ApiKeyService:
    async with get_db_context() as db:
        repo = ApiKeyRepository(db)
        return ApiKeyService(repo)


@router.post("", response_model=ApiKeyWithFullKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: ApiKeyCreateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    async with get_db_context() as db:
        repo = ApiKeyRepository(db)
        service = ApiKeyService(repo)
        result = await service.create_api_key(
            user_id=current_user["id"],
            name=request.name,
            expires_in_days=request.expires_in_days,
        )
        return ApiKeyWithFullKeyResponse(**result)


@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: dict = Depends(get_current_active_user),
):
    async with get_db_context() as db:
        repo = ApiKeyRepository(db)
        service = ApiKeyService(repo)
        keys = await service.list_user_api_keys(current_user["id"])
        return [ApiKeyResponse(**k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    async with get_db_context() as db:
        repo = ApiKeyRepository(db)
        service = ApiKeyService(repo)
        # Verify ownership before revoking
        keys = await service.list_user_api_keys(current_user["id"])
        key = next((k for k in keys if k["id"] == key_id), None)
        if not key:
            raise HTTPException(status_code=404, detail="API key not found")
        await service.revoke_api_key(key_id)
        return None