"""
Settings Sync Service

Syncs user settings and memory files across Claude Code environments.

Expanded module implementation with:
- types: Type definitions (SyncStatus, SyncDirection, SettingsConflict, etc.)
- storage: SettingsStorage for loading/saving settings to local storage
- diff: SettingsDiffer for detecting changes between settings
- conflict: ConflictResolver for handling sync conflicts
- watchdog: SettingsWatchdog for monitoring file changes
- config: Configuration management functions
- sync_engine: SettingsSyncEngine core sync orchestration
"""

from .types import (
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
    get_project_memory_key,
    get_project_settings_key,
)

from .storage import SettingsStorage

from .diff import SettingsDiffer

from .conflict import ConflictResolver

from .watchdog import SettingsWatchdog

from .config import (
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

from .sync_engine import SettingsSyncEngine

__all__ = [
    "ConflictResolution",
    "ConflictResolver",
    "DEFAULT_CONFIG",
    "SettingsConflict",
    "SettingsDiffer",
    "SettingsProfile",
    "SettingsStorage",
    "SettingsSyncConfig",
    "SettingsSyncEngine",
    "SettingsSyncFetchResult",
    "SettingsSyncUploadResult",
    "SettingsWatchdog",
    "SyncDirection",
    "SyncEntry",
    "SyncStatus",
    "SyncTrigger",
    "SYNC_KEYS",
    "UserSyncContent",
    "UserSyncData",
    "get_conflict_resolution_strategy",
    "get_config_dir",
    "get_config_file",
    "get_max_file_size_bytes",
    "get_max_retries",
    "get_project_memory_key",
    "get_project_settings_key",
    "get_sync_interval",
    "get_sync_settings",
    "get_timeout_ms",
    "is_auto_sync_enabled",
    "is_sync_enabled",
    "is_sync_in_background_enabled",
    "is_sync_on_startup_enabled",
    "load_sync_config",
    "save_sync_config",
    "set_sync_enabled",
    "update_sync_settings",
]
