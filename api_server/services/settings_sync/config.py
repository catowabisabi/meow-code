"""
Configuration management for settings sync.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .types import ConflictResolution, SettingsSyncConfig


DEFAULT_CONFIG = SettingsSyncConfig(
    enabled=False,
    sync_interval_seconds=300,
    max_retries=3,
    timeout_ms=10000,
    max_file_size_bytes=500 * 1024,
    auto_sync=True,
    sync_on_startup=True,
    conflict_resolution=ConflictResolution.LOCAL_WINS,
    sync_in_background=True,
)


def get_config_dir() -> Path:
    return Path.home() / ".claude" / "settings_sync"


def get_config_file() -> Path:
    return get_config_dir() / "sync_config.json"


def load_sync_config(config_file: Optional[Path] = None) -> SettingsSyncConfig:
    if config_file is None:
        config_file = get_config_file()

    if config_file.exists():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            return SettingsSyncConfig(**data)
        except (json.JSONDecodeError, OSError):
            return DEFAULT_CONFIG

    return DEFAULT_CONFIG


def save_sync_config(
    config: SettingsSyncConfig,
    config_file: Optional[Path] = None,
) -> bool:
    if config_file is None:
        config_file = get_config_file()

    config_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        config_file.write_text(
            json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return True
    except OSError:
        return False


def get_sync_settings(
    settings_file: Optional[Path] = None,
) -> Dict[str, Any]:
    if settings_file is None:
        settings_file = get_config_dir() / "settings.json"

    if settings_file.exists():
        try:
            return json.loads(settings_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    return {}


def update_sync_settings(
    updates: Dict[str, Any],
    settings_file: Optional[Path] = None,
) -> bool:
    if settings_file is None:
        settings_file = get_config_dir() / "settings.json"

    current = get_sync_settings(settings_file)
    current.update(updates)

    try:
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return True
    except OSError:
        return False


def get_sync_interval() -> int:
    config = load_sync_config()
    return config.sync_interval_seconds


def is_sync_enabled() -> bool:
    config = load_sync_config()
    return config.enabled


def set_sync_enabled(enabled: bool) -> bool:
    config = load_sync_config()
    config.enabled = enabled
    return save_sync_config(config)


def get_max_retries() -> int:
    config = load_sync_config()
    return config.max_retries


def get_timeout_ms() -> int:
    config = load_sync_config()
    return config.timeout_ms


def get_max_file_size_bytes() -> int:
    config = load_sync_config()
    return config.max_file_size_bytes


def get_conflict_resolution_strategy() -> ConflictResolution:
    config = load_sync_config()
    return config.conflict_resolution


def is_auto_sync_enabled() -> bool:
    config = load_sync_config()
    return config.auto_sync


def is_sync_on_startup_enabled() -> bool:
    config = load_sync_config()
    return config.sync_on_startup


def is_sync_in_background_enabled() -> bool:
    config = load_sync_config()
    return config.sync_in_background
