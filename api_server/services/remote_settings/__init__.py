"""Remote settings service module.

Provides functionality for fetching, caching, merging, and synchronizing
remote-managed settings for enterprise customers.

Based on TypeScript implementation in:
_claude_code_leaked_source_code/src/services/remoteManagedSettings/
"""

from .cache import SettingsCache
from .client import RemoteSettingsClient
from .config import (
    get_cache_ttl,
    get_max_retries,
    get_poll_interval,
    get_remote_settings_config,
    get_remote_url,
    get_settings_file_path,
    get_timeout_ms,
    load_remote_settings_config,
)
from .merge import SettingsMerger
from .policy import RemotePolicyManager
from .types import (
    EligibilityStatus,
    MergeStrategy,
    PolicyViolation,
    RemoteManagedSettingsFetchResult,
    RemotePolicy,
    RemoteSettingEntry,
    RemoteSettingsConfig,
    SettingsCacheEntry,
    SettingsSource,
    SettingsSyncStatus,
)
from .watchdog import SettingsWatchdog


__all__ = [
    "SettingsCache",
    "RemoteSettingsClient",
    "RemoteSettingsConfig",
    "RemoteSettingEntry",
    "SettingsSyncStatus",
    "RemotePolicy",
    "PolicyViolation",
    "SettingsSource",
    "MergeStrategy",
    "SettingsCacheEntry",
    "EligibilityStatus",
    "RemoteManagedSettingsFetchResult",
    "SettingsMerger",
    "RemotePolicyManager",
    "SettingsWatchdog",
    "get_remote_settings_config",
    "load_remote_settings_config",
    "get_remote_url",
    "get_poll_interval",
    "get_timeout_ms",
    "get_max_retries",
    "get_cache_ttl",
    "get_settings_file_path",
]
