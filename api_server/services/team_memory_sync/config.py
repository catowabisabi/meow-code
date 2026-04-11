"""Configuration management for team memory sync."""

import os
from typing import Optional

from .types import TeamMemoryConfig


DEFAULT_CONFIG = TeamMemoryConfig()


def load_team_memory_config() -> TeamMemoryConfig:
    config = TeamMemoryConfig(
        sync_enabled=_get_bool_env("TEAM_MEMORY_SYNC_ENABLED", True),
        sync_timeout_ms=_get_int_env("TEAM_MEMORY_SYNC_TIMEOUT_MS", 30_000),
        max_file_size_bytes=_get_int_env("TEAM_MEMORY_MAX_FILE_SIZE_BYTES", 250_000),
        max_put_body_bytes=_get_int_env("TEAM_MEMORY_MAX_PUT_BODY_BYTES", 200_000),
        max_retries=_get_int_env("TEAM_MEMORY_MAX_RETRIES", 3),
        max_conflict_retries=_get_int_env("TEAM_MEMORY_MAX_CONFLICT_RETRIES", 2),
        debounce_ms=_get_int_env("TEAM_MEMORY_DEBOUNCE_MS", 2000),
    )
    return config


def _get_bool_env(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes")


def _get_int_env(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


_sync_settings: Optional[TeamMemoryConfig] = None


def get_sync_settings() -> TeamMemoryConfig:
    global _sync_settings
    if _sync_settings is None:
        _sync_settings = load_team_memory_config()
    return _sync_settings


def update_sync_settings(config: TeamMemoryConfig) -> None:
    global _sync_settings
    _sync_settings = config


def reset_sync_settings() -> None:
    global _sync_settings
    _sync_settings = None
