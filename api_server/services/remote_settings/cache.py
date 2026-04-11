"""Cache management for remote settings."""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .types import SettingsCacheEntry, SettingsSource


class SettingsCache:
    _instance: Optional["SettingsCache"] = None
    _session_cache: Dict[str, SettingsCacheEntry] = {}
    _cache_file_path: Optional[Path] = None

    def __new__(cls) -> "SettingsCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._cache_file_path is None:
            from .config import get_settings_file_path
            self._cache_file_path = get_settings_file_path()

    @classmethod
    def get_instance(cls) -> "SettingsCache":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_cache_file_path(self) -> Path:
        return self._cache_file_path

    def set_cache_file_path(self, path: Path) -> None:
        self._cache_file_path = path

    def get_cached_settings(self, key: str) -> Optional[Any]:
        entry = self._session_cache.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and entry.expires_at < int(time.time() * 1000):
            del self._session_cache[key]
            return None
        return entry.value

    def set_cached_settings(
        self,
        key: str,
        value: Any,
        checksum: str,
        ttl_seconds: Optional[int] = None,
        source: SettingsSource = SettingsSource.REMOTE,
    ) -> None:
        now = int(time.time() * 1000)
        expires_at = None
        if ttl_seconds is not None:
            expires_at = now + (ttl_seconds * 1000)

        self._session_cache[key] = SettingsCacheEntry(
            key=key,
            value=value,
            checksum=checksum,
            cached_at=now,
            expires_at=expires_at,
            source=source,
        )

    def get_all_cached_settings(self) -> Dict[str, Any]:
        now = int(time.time() * 1000)
        result = {}
        expired_keys = []

        for key, entry in self._session_cache.items():
            if entry.expires_at is not None and entry.expires_at < now:
                expired_keys.append(key)
            else:
                result[key] = entry.value

        for key in expired_keys:
            del self._session_cache[key]

        return result

    def get_cache_entry(self, key: str) -> Optional[SettingsCacheEntry]:
        entry = self._session_cache.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and entry.expires_at < int(time.time() * 1000):
            del self._session_cache[key]
            return None
        return entry

    def invalidate_cache(self, key: Optional[str] = None) -> None:
        if key is None:
            self._session_cache.clear()
        elif key in self._session_cache:
            del self._session_cache[key]

    def get_cache_ttl(self, key: str) -> Optional[int]:
        entry = self.get_cache_entry(key)
        if entry is None or entry.expires_at is None:
            return None
        remaining = entry.expires_at - int(time.time() * 1000)
        return max(0, remaining)

    def load_from_file(self) -> Dict[str, Any]:
        if self._cache_file_path is None or not self._cache_file_path.exists():
            return {}

        try:
            content = self._cache_file_path.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                return {}

            now = int(time.time() * 1000)
            for key, value in data.items():
                if isinstance(value, dict) and "cached_at" in value:
                    cached_at = value.get("cached_at", 0)
                    expires_at = value.get("expires_at")
                    if expires_at is not None and expires_at < now:
                        continue
                    self._session_cache[key] = SettingsCacheEntry(
                        key=key,
                        value=value.get("value"),
                        checksum=value.get("checksum", ""),
                        cached_at=cached_at,
                        expires_at=expires_at,
                        source=SettingsSource(value.get("source", "remote")),
                    )
                else:
                    self._session_cache[key] = SettingsCacheEntry(
                        key=key,
                        value=value,
                        checksum="",
                        cached_at=now,
                        source=SettingsSource.REMOTE,
                    )
            return {k: v.value for k, v in self._session_cache.items()}
        except (json.JSONDecodeError, OSError):
            return {}

    def save_to_file(self, settings: Dict[str, Any], checksum: str) -> None:
        if self._cache_file_path is None:
            return

        self._cache_file_path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        now = int(time.time() * 1000)
        for key, value in settings.items():
            entry = self._session_cache.get(key)
            if entry:
                data[key] = {
                    "value": entry.value,
                    "checksum": entry.checksum,
                    "cached_at": entry.cached_at,
                    "expires_at": entry.expires_at,
                    "source": entry.source.value,
                }
            else:
                data[key] = {
                    "value": value,
                    "checksum": checksum,
                    "cached_at": now,
                    "expires_at": None,
                    "source": SettingsSource.REMOTE.value,
                }

        try:
            self._cache_file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def clear_file_cache(self) -> None:
        if self._cache_file_path and self._cache_file_path.exists():
            try:
                self._cache_file_path.unlink()
            except OSError:
                pass

    def get_checksum(self, key: str) -> Optional[str]:
        entry = self.get_cache_entry(key)
        return entry.checksum if entry else None

    def has_valid_cache(self) -> bool:
        return len(self._session_cache) > 0
