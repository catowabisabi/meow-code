import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class RemoteSetting(BaseModel):
    key: str
    value: Any
    updatedAt: int
    source: str
    is_override: bool = False


class RemoteSettingsService:
    _settings: Dict[str, RemoteSetting] = {}
    _last_fetch: Optional[float] = None
    _remote_url: Optional[str] = None
    
    @classmethod
    def _get_settings_file(cls) -> Path:
        d = Path.home() / ".claude" / "remote_settings"
        d.mkdir(parents=True, exist_ok=True)
        return d / "settings.json"
    
    @classmethod
    async def _load_settings(cls) -> None:
        path = cls._get_settings_file()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                cls._settings = {
                    k: RemoteSetting(**v) 
                    for k, v in data.get("settings", {}).items()
                }
                cls._last_fetch = data.get("last_fetch")
                cls._remote_url = data.get("remote_url")
            except (json.JSONDecodeError, OSError):
                pass
    
    @classmethod
    async def _save_settings(cls) -> None:
        path = cls._get_settings_file()
        data = {
            "settings": {k: v.model_dump() for k, v in cls._settings.items()},
            "last_fetch": cls._last_fetch,
            "remote_url": cls._remote_url,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    @classmethod
    async def set_remote_url(cls, url: str) -> None:
        cls._remote_url = url
        await cls._load_settings()
    
    @classmethod
    async def fetch_from_remote(cls, url: Optional[str] = None) -> bool:
        url = url or cls._remote_url
        if not url:
            return False
        
        await cls._load_settings()
        cls._last_fetch = datetime.utcnow().timestamp()
        
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                for key, value in data.get("settings", {}).items():
                    cls._settings[key] = RemoteSetting(
                        key=key,
                        value=value,
                        updatedAt=cls._last_fetch,
                        source=url,
                        is_override=False,
                    )
                await cls._save_settings()
                return True
        except Exception:
            return False
    
    @classmethod
    async def get_setting(cls, key: str, default: Any = None) -> Any:
        await cls._load_settings()
        setting = cls._settings.get(key)
        if setting:
            return setting.value
        return default
    
    @classmethod
    async def set_setting(
        cls,
        key: str,
        value: Any,
        is_override: bool = False,
    ) -> None:
        await cls._load_settings()
        cls._settings[key] = RemoteSetting(
            key=key,
            value=value,
            updatedAt=int(datetime.utcnow().timestamp() * 1000),
            source="local",
            is_override=is_override,
        )
        await cls._save_settings()
    
    @classmethod
    async def delete_setting(cls, key: str) -> bool:
        await cls._load_settings()
        if key in cls._settings:
            del cls._settings[key]
            await cls._save_settings()
            return True
        return False
    
    @classmethod
    async def get_all_settings(cls) -> Dict[str, Any]:
        await cls._load_settings()
        return {k: v.value for k, v in cls._settings.items()}
    
    @classmethod
    async def get_overrides(cls) -> Dict[str, Any]:
        await cls._load_settings()
        return {
            k: v.value 
            for k, v in cls._settings.items() 
            if v.is_override
        }
    
    @classmethod
    async def clear_local_overrides(cls) -> None:
        await cls._load_settings()
        to_remove = [k for k, v in cls._settings.items() if v.is_override and v.source == "local"]
        for k in to_remove:
            del cls._settings[k]
        await cls._save_settings()