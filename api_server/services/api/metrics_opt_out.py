"""
Metrics opt-out service for checking if metrics are enabled.
"""

import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

import httpx


CACHE_TTL_MS = 60 * 60 * 1000
DISK_CACHE_TTL_MS = 24 * 60 * 60 * 1000


@dataclass
class MetricsEnabledResponse:
    metrics_logging_enabled: bool = False


@dataclass
class MetricsStatus:
    enabled: bool = False
    has_error: bool = False


_metrics_cache: Optional[MetricsStatus] = None


def _get_auth_headers() -> Dict[str, Any]:
    return {"headers": {}, "error": None}


def _log_for_debugging(message: str) -> None:
    print(f"[metrics] {message}", flush=True)


def _log_error(err: Exception) -> None:
    print(f"[metrics] Error: {err}", flush=True)


def _is_essential_traffic_only() -> bool:
    return os.environ.get("CLAUDE_CODE_ESSENTIAL_TRAFFIC_ONLY", "").lower() in ("true", "1", "yes")


def _is_claude_ai_subscriber() -> bool:
    return True


def _has_profile_scope() -> bool:
    return True


def _get_global_config() -> Dict[str, Any]:
    return {}


def _save_global_config(updater) -> None:
    pass


def _get_claude_code_user_agent() -> str:
    return os.environ.get("CLAUDE_CODE_USER_AGENT", "Claude Code/1.0")


async def _fetch_metrics_enabled_impl() -> MetricsEnabledResponse:
    auth_result = _get_auth_headers()
    if auth_result.get("error"):
        raise Exception(f"Auth error: {auth_result['error']}")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": _get_claude_code_user_agent(),
        **auth_result.get("headers", {}),
    }

    endpoint = "https://api.anthropic.com/api/claude_code/organizations/metrics_enabled"

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(endpoint, headers=headers)

    if response.status_code == 200:
        return MetricsEnabledResponse(**response.json())
    raise Exception(f"Failed to fetch metrics status: {response.status_code}")


async def _check_metrics_enabled_api() -> MetricsStatus:
    if _is_essential_traffic_only():
        return MetricsStatus(enabled=False, has_error=False)

    try:
        data = await _fetch_metrics_enabled_impl()

        _log_for_debugging(
            f"Metrics opt-out API response: enabled={data.metrics_logging_enabled}",
        )

        return MetricsStatus(enabled=data.metrics_logging_enabled, has_error=False)
    except Exception as error:
        _log_for_debugging(f"Failed to check metrics opt-out status: {error}")
        _log_error(error)
        return MetricsStatus(enabled=False, has_error=True)


async def _check_metrics_enabled_cached() -> MetricsStatus:
    global _metrics_cache

    if _metrics_cache is not None:
        return _metrics_cache

    result = await _check_metrics_enabled_api()
    _metrics_cache = result
    return result


async def refresh_metrics_status() -> MetricsStatus:
    result = await _check_metrics_enabled_cached()
    if result.has_error:
        return result

    cached = _get_global_config().get("metricsStatusCache")
    unchanged = cached is not None and cached.get("enabled") == result.enabled
    if unchanged and cached:
        if time.time() * 1000 - cached.get("timestamp", 0) < DISK_CACHE_TTL_MS:
            return result

    def updater(current: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **current,
            "metricsStatusCache": {
                "enabled": result.enabled,
                "timestamp": time.time() * 1000,
            },
        }

    _save_global_config(updater)
    return result


async def check_metrics_enabled() -> MetricsStatus:
    if _is_claude_ai_subscriber() and not _has_profile_scope():
        return MetricsStatus(enabled=False, has_error=False)

    cached = _get_global_config().get("metricsStatusCache")
    if cached:
        if time.time() * 1000 - cached.get("timestamp", 0) > DISK_CACHE_TTL_MS:
            try:
                await refresh_metrics_status()
            except Exception:
                pass
        return MetricsStatus(enabled=cached.get("enabled", False), has_error=False)

    return await refresh_metrics_status()


def _clear_metrics_enabled_cache_for_testing() -> None:
    global _metrics_cache
    _metrics_cache = None
