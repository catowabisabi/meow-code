from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from api_server.services.oauth import OAuthService, OAuthProvider
from api_server.middleware.auth import get_current_active_user

router = APIRouter(prefix="/oauth", tags=["oauth"])

oauth_service = OAuthService()


class TokenRequest(BaseModel):
    code: str


@router.get("/authorize/{provider}")
async def authorize(provider: str):
    try:
        url = oauth_service.get_authorization_url(provider)
        return RedirectResponse(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback/{provider}")
async def callback(provider: str, code: str = Query(...)):
    try:
        token = await oauth_service.exchange_code(provider, code)
        user = await oauth_service.get_user_info(provider, token.access_token)
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "provider": user.provider,
            },
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh")
async def refresh(provider: str, refresh_token: str):
    try:
        token = await oauth_service.refresh_token(provider, refresh_token)
        return {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
async def get_oauth_user(
    provider: str,
    current_user: dict = Depends(get_current_active_user),
):
    access_token = current_user.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token")

    try:
        user = await oauth_service.get_user_info(provider, access_token)
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "provider": user.provider,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))