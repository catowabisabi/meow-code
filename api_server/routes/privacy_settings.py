import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api_server.services.analytics import log_event

router = APIRouter(prefix="/privacy-settings", tags=["privacy-settings"])

PRIVACY_SETTINGS_PATH = Path.home() / ".claude" / "privacy-settings.json"


class GroveSettings(BaseModel):
    grove_enabled: Optional[bool] = None
    domain_excluded: Optional[list[str]] = None


class PrivacySettingsResponse(BaseModel):
    qualified: bool
    settings: GroveSettings
    message: Optional[str] = None


class PrivacySettingsUpdate(BaseModel):
    grove_enabled: bool


def _load_privacy_settings() -> GroveSettings:
    try:
        if PRIVACY_SETTINGS_PATH.exists():
            with open(PRIVACY_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return GroveSettings(**data)
    except Exception:
        pass
    return GroveSettings()


def _save_privacy_settings(settings: GroveSettings) -> None:
    PRIVACY_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PRIVACY_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, indent=2)


def _is_qualified_for_grove() -> bool:
    return True


@router.get("")
async def get_privacy_settings() -> PrivacySettingsResponse:
    qualified = _is_qualified_for_grove()
    settings = _load_privacy_settings()

    if not qualified:
        return PrivacySettingsResponse(
            qualified=False,
            settings=settings,
            message="Review and manage your privacy settings at https://claude.ai/settings/data-privacy-controls",
        )

    return PrivacySettingsResponse(
        qualified=True,
        settings=settings,
        message=None,
    )


@router.put("")
async def update_privacy_settings(update: PrivacySettingsUpdate) -> PrivacySettingsResponse:
    try:
        settings = _load_privacy_settings()
        previous_grove_enabled = settings.grove_enabled
        settings.grove_enabled = update.grove_enabled

        _save_privacy_settings(settings)

        if previous_grove_enabled is not None and previous_grove_enabled != update.grove_enabled:
            log_event(
                "tengu_grove_policy_toggled",
                {
                    "state": update.grove_enabled,
                    "location": "settings",
                },
            )

        return PrivacySettingsResponse(
            qualified=True,
            settings=settings,
            message=None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))