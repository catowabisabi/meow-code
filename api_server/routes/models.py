"""
FastAPI routes for model provider management.
"""
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/models", tags=["models"])

MODELS_CONFIG_PATH = Path.home() / ".claude" / "models.json"


class Provider(BaseModel):
    type: str
    displayName: Optional[str] = None
    baseUrl: str
    apiKey: str = ""
    models: list[str] = []
    enabled: bool = True


class ProviderCreate(BaseModel):
    id: str
    type: str
    displayName: Optional[str] = None
    baseUrl: str
    apiKey: str = ""
    models: list[str] = []


class ProviderUpdate(BaseModel):
    type: Optional[str] = None
    displayName: Optional[str] = None
    baseUrl: Optional[str] = None
    apiKey: Optional[str] = None
    models: Optional[list[str]] = None
    enabled: Optional[bool] = None


class DefaultModelUpdate(BaseModel):
    model: str
    provider: str


class HotkeyEntry(BaseModel):
    key: str
    model: str
    provider: str


class HotkeysUpdate(BaseModel):
    hotkeys: list[HotkeyEntry]


class ModelsConfigResponse(BaseModel):
    providers: dict[str, Provider]
    availableModels: list[str]
    defaultModel: Optional[str] = None
    defaultProvider: Optional[str] = None
    hotkeys: list[dict]
    knownProviders: list[str]


KNOWN_PROVIDERS = [
    "anthropic",
    "openai",
    "azure-openai",
    "google",
    "ollama",
    "lmstudio",
    "openrouter",
    "deepseek",
]


def _load_config() -> dict:
    if not MODELS_CONFIG_PATH.exists():
        return {
            "providers": {},
            "defaultModel": None,
            "defaultProvider": None,
            "hotkeys": [],
        }
    try:
        with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {
            "providers": {},
            "defaultModel": None,
            "defaultProvider": None,
            "hotkeys": [],
        }


def _save_config(config: dict) -> None:
    MODELS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODELS_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _get_available_models() -> list[str]:
    config = _load_config()
    models = set()
    for p in config.get("providers", {}).values():
        models.update(p.get("models", []))
    return sorted(list(models))


@router.get("", response_model=ModelsConfigResponse)
async def get_models():
    config = _load_config()
    providers = {}
    for pid, pdata in config.get("providers", {}).items():
        providers[pid] = Provider(
            type=pdata.get("type", ""),
            displayName=pdata.get("displayName", pid),
            baseUrl=pdata.get("baseUrl", ""),
            apiKey=pdata.get("apiKey", ""),
            models=pdata.get("models", []),
            enabled=pdata.get("enabled", True),
        )
    return ModelsConfigResponse(
        providers=providers,
        availableModels=_get_available_models(),
        defaultModel=config.get("defaultModel"),
        defaultProvider=config.get("defaultProvider"),
        hotkeys=config.get("hotkeys", []),
        knownProviders=KNOWN_PROVIDERS,
    )


@router.post("")
async def add_provider(data: ProviderCreate):
    if not data.id or not data.type or not data.baseUrl:
        raise HTTPException(status_code=400, detail="Missing required fields: id, type, baseUrl")

    config = _load_config()
    config["providers"][data.id] = {
        "type": data.type,
        "displayName": data.displayName or data.id,
        "baseUrl": data.baseUrl,
        "apiKey": data.apiKey or "",
        "models": data.models or [],
        "enabled": True,
    }
    _save_config(config)

    providers = {}
    for pid, pdata in config.get("providers", {}).items():
        providers[pid] = Provider(
            type=pdata.get("type", ""),
            displayName=pdata.get("displayName", pid),
            baseUrl=pdata.get("baseUrl", ""),
            apiKey=pdata.get("apiKey", ""),
            models=pdata.get("models", []),
            enabled=pdata.get("enabled", True),
        )
    return {"ok": True, "providers": providers}


@router.put("/{provider_id}")
async def update_provider(provider_id: str, data: ProviderUpdate):
    config = _load_config()
    if provider_id not in config.get("providers", {}):
        raise HTTPException(status_code=404, detail=f'Provider "{provider_id}" not found')

    existing = config["providers"][provider_id]
    update_data = data.model_dump(exclude_unset=True)
    updated = {**existing, **update_data}
    config["providers"][provider_id] = updated
    _save_config(config)

    return {"ok": True, "provider": Provider(**updated)}


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str):
    config = _load_config()
    if provider_id in config.get("providers", {}):
        del config["providers"][provider_id]
        _save_config(config)

    providers = {}
    for pid, pdata in config.get("providers", {}).items():
        providers[pid] = Provider(
            type=pdata.get("type", ""),
            displayName=pdata.get("displayName", pid),
            baseUrl=pdata.get("baseUrl", ""),
            apiKey=pdata.get("apiKey", ""),
            models=pdata.get("models", []),
            enabled=pdata.get("enabled", True),
        )
    return {"ok": True, "providers": providers}


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str):
    config = _load_config()
    if provider_id not in config.get("providers", {}):
        raise HTTPException(status_code=404, detail=f'Provider "{provider_id}" not found')

    return {"ok": True, "message": "Connection test not implemented - mock response"}


@router.put("/default")
async def set_default_model(data: DefaultModelUpdate):
    config = _load_config()
    config["defaultModel"] = data.model
    config["defaultProvider"] = data.provider
    _save_config(config)
    return {"ok": True, "defaultModel": data.model, "defaultProvider": data.provider}


@router.put("/hotkeys")
async def update_hotkeys(data: HotkeysUpdate):
    config = _load_config()
    config["hotkeys"] = [h.model_dump() for h in data.hotkeys]
    _save_config(config)
    return {"ok": True, "hotkeys": config["hotkeys"]}
