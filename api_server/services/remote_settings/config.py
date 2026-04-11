"""Configuration functions for remote settings service."""

import os
from pathlib import Path
from typing import Optional

from .types import RemoteSettingsConfig


DEFAULT_REMOTE_URL = "https://api.claude.ai/api/claude_code/settings"
DEFAULT_POLL_INTERVAL_MS = 60 * 60 * 1000
DEFAULT_TIMEOUT_MS = 10000
DEFAULT_MAX_RETRIES = 5
DEFAULT_CACHE_TTL_SECONDS = 3600


def get_remote_settings_config() -> RemoteSettingsConfig:
    """Load remote settings configuration from environment variables."""
    return RemoteSettingsConfig(
        remote_url=_get_remote_url(),
        enabled=_is_enabled(),
        poll_interval_ms=_get_poll_interval(),
        timeout_ms=_get_timeout(),
        max_retries=_get_max_retries(),
        cache_ttl_seconds=_get_cache_ttl(),
        use_etag=True,
        fail_open=True,
    )


def _get_remote_url() -> Optional[str]:
    return os.environ.get("CLAUDE_REMOTE_SETTINGS_URL") or os.environ.get(
        "CLAUDE_CODE_REMOTE_SETTINGS_URL"
    )


def _is_enabled() -> bool:
    env_val = os.environ.get("CLAUDE_REMOTE_SETTINGS_ENABLED", "true").lower()
    return env_val in ("true", "1", "yes")


def _get_poll_interval() -> int:
    val = os.environ.get("CLAUDE_REMOTE_SETTINGS_POLL_INTERVAL_MS")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return DEFAULT_POLL_INTERVAL_MS


def _get_timeout() -> int:
    val = os.environ.get("CLAUDE_REMOTE_SETTINGS_TIMEOUT_MS")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return DEFAULT_TIMEOUT_MS


def _get_max_retries() -> int:
    val = os.environ.get("CLAUDE_REMOTE_SETTINGS_MAX_RETRIES")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return DEFAULT_MAX_RETRIES


def _get_cache_ttl() -> int:
    val = os.environ.get("CLAUDE_REMOTE_SETTINGS_CACHE_TTL_SECONDS")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return DEFAULT_CACHE_TTL_SECONDS


def get_remote_url() -> Optional[str]:
    """Get the remote settings URL from config."""
    return get_remote_settings_config().remote_url


def get_poll_interval() -> int:
    """Get the poll interval in milliseconds."""
    return get_remote_settings_config().poll_interval_ms


def get_timeout_ms() -> int:
    """Get the request timeout in milliseconds."""
    return get_remote_settings_config().timeout_ms


def get_max_retries() -> int:
    """Get the maximum number of retries."""
    return get_remote_settings_config().max_retries


def get_cache_ttl() -> int:
    """Get the cache TTL in seconds."""
    return get_remote_settings_config().cache_ttl_seconds


def get_settings_file_path() -> Path:
    """Get the path to the remote settings cache file."""
    config_home = os.environ.get("CLAUDE_CONFIG_HOME") or os.path.expanduser("~/.config/claude")
    return Path(config_home) / "remote-settings.json"


def load_remote_settings_config() -> RemoteSettingsConfig:
    """Load remote settings configuration (alias for get_remote_settings_config)."""
    return get_remote_settings_config()
