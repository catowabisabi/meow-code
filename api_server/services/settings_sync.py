"""
Settings Sync Service (backwards-compatible wrapper)

This module has been expanded into a package at settings_sync/.
The original SettingsSyncService class is preserved here for backwards compatibility.
New code should import from settings_sync directly.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .settings_sync.types import (
    ConflictResolution,
    SettingsConflict,
    SettingsProfile,
    SettingsSyncConfig,
    SettingsSyncFetchResult,
    SettingsSyncUploadResult,
    SyncDirection,
    SyncEntry,
    SyncStatus,
    SyncTrigger,
    SYNC_KEYS,
    UserSyncContent,
    UserSyncData,
)
from .settings_sync.storage import SettingsStorage
from .settings_sync.diff import SettingsDiffer
from .settings_sync.conflict import ConflictResolver
from .settings_sync.watchdog import SettingsWatchdog
from .settings_sync.config import (
    DEFAULT_CONFIG,
    get_conflict_resolution_strategy,
    get_config_dir,
    get_config_file,
    get_max_file_size_bytes,
    get_max_retries,
    get_sync_interval,
    get_sync_settings,
    get_timeout_ms,
    is_auto_sync_enabled,
    is_sync_enabled,
    is_sync_in_background_enabled,
    is_sync_on_startup_enabled,
    load_sync_config,
    save_sync_config,
    set_sync_enabled,
    update_sync_settings,
)
from .settings_sync.sync_engine import SettingsSyncEngine


class SettingsSyncService:
    _profiles: Dict[str, SettingsProfile] = {}
    _active_profile_id: Optional[str] = None
    _last_sync: Optional[float] = None
    _engine: Optional[SettingsSyncEngine] = None
    _storage: Optional[SettingsStorage] = None

    @classmethod
    def _get_config_dir(cls) -> Path:
        d = Path.home() / ".claude" / "settings_sync"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @classmethod
    def _get_storage(cls) -> SettingsStorage:
        if cls._storage is None:
            cls._storage = SettingsStorage(cls._get_config_dir())
        return cls._storage

    @classmethod
    def _get_engine(cls) -> SettingsSyncEngine:
        if cls._engine is None:
            cls._engine = SettingsSyncEngine(
                config=load_sync_config(),
                storage=cls._get_storage(),
            )
        return cls._engine

    @classmethod
    def _get_profiles_file(cls) -> Path:
        return cls._get_config_dir() / "profiles.json"

    @classmethod
    async def _load_profiles(cls) -> None:
        storage = cls._get_storage()
        cls._profiles = storage.load_profiles()

    @classmethod
    async def _save_profiles(cls) -> None:
        storage = cls._get_storage()
        storage.save_profiles(
            cls._profiles,
            active_profile_id=cls._active_profile_id,
            last_sync=cls._last_sync,
        )

    @classmethod
    async def create_profile(
        cls,
        name: str,
        settings: Optional[Dict[str, Any]] = None,
    ) -> SettingsProfile:
        await cls._load_profiles()

        profile_id = f"profile_{datetime.utcnow().timestamp()}"
        profile = SettingsProfile(
            profile_id=profile_id,
            name=name,
            settings=settings or {},
            createdAt=int(datetime.utcnow().timestamp() * 1000),
            updatedAt=int(datetime.utcnow().timestamp() * 1000),
            is_active=False,
        )
        cls._profiles[profile_id] = profile
        await cls._save_profiles()
        return profile

    @classmethod
    async def get_profile(cls, profile_id: str) -> Optional[SettingsProfile]:
        await cls._load_profiles()
        return cls._profiles.get(profile_id)

    @classmethod
    async def update_profile(
        cls,
        profile_id: str,
        settings: Dict[str, Any],
    ) -> Optional[SettingsProfile]:
        await cls._load_profiles()
        if profile_id not in cls._profiles:
            return None

        profile = cls._profiles[profile_id]
        profile.settings.update(settings)
        profile.updatedAt = int(datetime.utcnow().timestamp() * 1000)
        await cls._save_profiles()
        return profile

    @classmethod
    async def delete_profile(cls, profile_id: str) -> bool:
        await cls._load_profiles()
        if profile_id in cls._profiles:
            del cls._profiles[profile_id]
            if cls._active_profile_id == profile_id:
                cls._active_profile_id = None
            await cls._save_profiles()
            return True
        return False

    @classmethod
    async def set_active_profile(cls, profile_id: str) -> bool:
        await cls._load_profiles()
        if profile_id not in cls._profiles:
            return False

        for p in cls._profiles.values():
            p.is_active = False
        cls._profiles[profile_id].is_active = True
        cls._active_profile_id = profile_id
        cls._last_sync = datetime.utcnow().timestamp()
        await cls._save_profiles()
        return True

    @classmethod
    async def get_active_settings(cls) -> Dict[str, Any]:
        await cls._load_profiles()
        if cls._active_profile_id and cls._active_profile_id in cls._profiles:
            return cls._profiles[cls._active_profile_id].settings
        return {}

    @classmethod
    async def list_profiles(cls) -> list[SettingsProfile]:
        await cls._load_profiles()
        return list(cls._profiles.values())

    @classmethod
    async def sync_to_remote(cls, remote_url: str) -> bool:
        engine = cls._get_engine()
        result = await engine.sync(
            direction=SyncDirection.TO_REMOTE,
            trigger=SyncTrigger.MANUAL,
            remote_url=remote_url,
        )
        return result

    @classmethod
    async def sync_from_remote(cls, remote_url: str) -> bool:
        engine = cls._get_engine()
        result = await engine.sync(
            direction=SyncDirection.FROM_REMOTE,
            trigger=SyncTrigger.MANUAL,
            remote_url=remote_url,
        )
        return result

    @classmethod
    async def sync(cls) -> bool:
        engine = cls._get_engine()
        result = await engine.sync(
            direction=SyncDirection.BIDIRECTIONAL,
            trigger=SyncTrigger.MANUAL,
        )
        return result


__all__ = [
    "SettingsSyncService",
    "SettingsSyncEngine",
    "SettingsStorage",
    "SettingsDiffer",
    "ConflictResolver",
    "SettingsWatchdog",
    "SettingsSyncConfig",
    "SettingsProfile",
    "SyncEntry",
    "SyncStatus",
    "SyncDirection",
    "SyncTrigger",
    "ConflictResolution",
    "SettingsConflict",
    "UserSyncData",
    "UserSyncContent",
    "SettingsSyncFetchResult",
    "SettingsSyncUploadResult",
    "SYNC_KEYS",
    "DEFAULT_CONFIG",
    "load_sync_config",
    "save_sync_config",
    "get_sync_settings",
    "update_sync_settings",
    "get_sync_interval",
    "is_sync_enabled",
    "set_sync_enabled",
    "get_max_retries",
    "get_timeout_ms",
    "get_max_file_size_bytes",
    "get_conflict_resolution_strategy",
    "is_auto_sync_enabled",
    "is_sync_on_startup_enabled",
    "is_sync_in_background_enabled",
    "get_config_dir",
    "get_config_file",
]
