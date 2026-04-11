import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db.settings_db import (
    get_api_credential, set_api_credential,
    has_any_api_key, get_all_api_credentials,
)

router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


class Hotkey(BaseModel):
    key: str
    model: str
    provider: str


class Settings(BaseModel):
    port: int = 18792
    defaultModel: str = ""
    defaultProvider: str = ""
    hotkeys: List[Hotkey] = []
    language: str = ""
    systemPrompt: str = ""


class UserSettings(BaseModel):
    language: str = ""
    systemPrompt: str = ""


class SettingsUpdate(BaseModel):
    port: Optional[int] = None
    defaultModel: Optional[str] = None
    defaultProvider: Optional[str] = None
    hotkeys: Optional[List[Hotkey]] = None
    language: Optional[str] = None
    systemPrompt: Optional[str] = None


def _load_user_settings() -> UserSettings:
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return UserSettings(**data)
    except Exception:
        pass
    return UserSettings()


def _save_user_settings(settings: UserSettings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, indent=2)


def _get_settings() -> Settings:
    user_settings = _load_user_settings()
    settings = Settings(
        port=18792,
        defaultModel="",
        defaultProvider="",
        hotkeys=[],
        language=user_settings.language,
        systemPrompt=user_settings.systemPrompt,
    )
    return settings


@router.get("")
async def get_settings() -> Settings:
    return _get_settings()


@router.put("")
async def update_settings(update: SettingsUpdate) -> dict:
    try:
        settings = _get_settings()
        user_settings = _load_user_settings()

        if update.port is not None:
            settings.port = update.port
        if update.defaultModel is not None:
            settings.defaultModel = update.defaultModel
        if update.defaultProvider is not None:
            settings.defaultProvider = update.defaultProvider
        if update.hotkeys is not None:
            settings.hotkeys = update.hotkeys
        if update.language is not None:
            settings.language = update.language
            user_settings.language = update.language
        if update.systemPrompt is not None:
            settings.systemPrompt = update.systemPrompt
            user_settings.systemPrompt = update.systemPrompt

        _save_user_settings(user_settings)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ApiCredentialRequest(BaseModel):
    provider: str
    api_key: str
    base_url: Optional[str] = None
    extra_config: Optional[dict] = None


@router.get("/api-key-status")
async def get_api_key_status():
    has_key = has_any_api_key()
    return {
        "has_api_key": has_key,
        "needs_configuration": not has_key
    }


@router.post("/api-credentials")
async def save_api_credentials(cred: ApiCredentialRequest):
    set_api_credential(cred.provider, cred.api_key, cred.base_url, cred.extra_config)
    # Invalidate cached adapter router so new credentials take effect
    try:
        from api_server.adapters import router as router_module
        if hasattr(router_module, 'adapter_router'):
            delattr(router_module, 'adapter_router')
    except Exception:
        pass
    return {"ok": True, "provider": cred.provider}


@router.get("/api-credentials")
async def list_api_credentials():
    creds = get_all_api_credentials()
    return [{
        "provider": c["provider"],
        "has_key": bool(c["api_key"]),
        "base_url": c["base_url"]
    } for c in creds]


@router.get("/api-credentials/{provider}")
async def get_api_credential_by_provider(provider: str):
    cred = get_api_credential(provider)
    if not cred:
        raise HTTPException(status_code=404, detail="Provider not configured")
    return cred


@router.get("/setup-required")
async def check_setup_required():
    return {"setup_required": not has_any_api_key()}
