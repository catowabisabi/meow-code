from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
from api_server.services.api_key import ApiKeyService
from api_server.db.repositories.api_key import ApiKeyRepository
from api_server.db import get_db
from api_server.middleware.auth import get_current_active_user
from sqlalchemy.ext.asyncio import AsyncSession

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

async def get_api_key_service(db: AsyncSession = Depends(get_db)) -> ApiKeyService:
    repo = ApiKeyRepository(db)
    return ApiKeyService(repo)

@router.post("", response_model=ApiKeyWithFullKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: ApiKeyCreateRequest,
    current_user: dict = Depends(get_current_active_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    result = await api_key_service.create_api_key(
        user_id=current_user["id"],
        name=request.name,
        expires_in_days=request.expires_in_days,
    )
    return ApiKeyWithFullKeyResponse(**result)

@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: dict = Depends(get_current_active_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    keys = await api_key_service.list_user_api_keys(current_user["id"])
    return [ApiKeyResponse(**k) for k in keys]

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_active_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    await api_key_service.revoke_api_key(key_id)
    return None