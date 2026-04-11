"""
Grove notification service for managing user settings and configuration.

Provides functionality to check Grove eligibility, manage notice viewing,
and determine whether to show Grove dialogs to users.
"""

import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable

import httpx


# Cache expiration: 24 hours
GROVE_CACHE_EXPIRATION_MS = 24 * 60 * 60 * 1000


@dataclass
class AccountSettings:
    """User account settings related to Grove."""
    grove_enabled: Optional[bool] = None
    grove_notice_viewed_at: Optional[str] = None


@dataclass
class GroveConfig:
    """Grove Statsig configuration from API."""
    grove_enabled: bool = False
    domain_excluded: bool = False
    notice_is_grace_period: bool = True
    notice_reminder_frequency: Optional[int] = None


# Type alias for the generic ApiResult
ApiResult = Dict[str, Any]


def _get_oauth_config() -> Dict[str, str]:
    """Get OAuth configuration."""
    return {
        "BASE_API_URL": os.environ.get("CLAUDE_CODE_API_BASE_URL", "https://api.claude.ai"),
    }


def _get_auth_headers() -> Dict[str, Any]:
    """Get authentication headers placeholder."""
    # In production, this would use actual auth implementation
    return {"headers": {}, "error": None}


def _get_user_agent() -> str:
    """Get Claude Code user agent."""
    return os.environ.get("CLAUDE_CODE_USER_AGENT", "Claude Code")


def _log_error(err: Exception) -> None:
    """Log error for debugging."""
    print(f"[grove] Error: {err}", flush=True)


def _log_for_debugging(message: str) -> None:
    """Log debug message."""
    print(f"[grove] {message}", flush=True)


def _is_essential_traffic_only() -> bool:
    """Check if only essential traffic should be processed."""
    return os.environ.get("CLAUDE_CODE_ESSENTIAL_TRAFFIC_ONLY", "").lower() in ("true", "1", "yes")


def _with_oauth401_retry(func: Callable) -> Callable:
    """Wrapper for OAuth 401 retry logic (placeholder)."""
    return func


def _get_global_config() -> Dict[str, Any]:
    """Get global configuration (placeholder)."""
    return {}


def _save_global_config(updater: Callable) -> None:
    """Save global configuration (placeholder)."""
    pass


def _is_consumer_subscriber() -> bool:
    """Check if user is a consumer subscriber."""
    return True


def _get_oauth_account_info() -> Optional[Dict[str, Any]]:
    """Get OAuth account info (placeholder)."""
    return None


def _get_claude_code_user_agent() -> str:
    """Get Claude Code user agent."""
    return os.environ.get("CLAUDE_CODE_USER_AGENT", "Claude Code/1.0")


# Module-level cache for get_grove_settings
_grove_settings_cache: Optional[Dict[str, Any]] = None


async def _fetch_grove_settings_impl() -> Dict[str, Any]:
    """
    Internal implementation to fetch Grove settings from API.
    Returns ApiResult to distinguish between API failure and success.
    """
    if _is_essential_traffic_only():
        return {"success": False}

    try:
        auth_headers = _get_auth_headers()
        if auth_headers.get("error"):
            raise Exception(f"Failed to get auth headers: {auth_headers['error']}")

        config = _get_oauth_config()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{config['BASE_API_URL']}/api/oauth/account/settings",
                headers={
                    **auth_headers.get("headers", {}),
                    "User-Agent": _get_claude_code_user_agent(),
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data}
            else:
                _log_error(Exception(f"API returned {response.status_code}"))
                return {"success": False}
    except Exception as err:
        _log_error(err)
        # Clear cache on failure to avoid locking user out of privacy settings
        global _grove_settings_cache
        _grove_settings_cache = None
        return {"success": False}


async def get_grove_settings() -> Dict[str, Any]:
    """
    Get the current Grove settings for the user account.
    Returns ApiResult to distinguish between API failure and success.
    Uses memoization for the session to avoid redundant per-render requests.
    Cache is invalidated in update_grove_settings() so post-toggle reads are fresh.
    """
    global _grove_settings_cache
    
    if _grove_settings_cache is not None:
        return _grove_settings_cache
    
    result = await _fetch_grove_settings_impl()
    _grove_settings_cache = result
    return result


def mark_grove_settings_cache_dirty() -> None:
    """Mark the grove settings cache as dirty so it will be refetched."""
    global _grove_settings_cache
    _grove_settings_cache = None


async def mark_grove_notice_viewed() -> None:
    """
    Mark that the Grove notice has been viewed by the user.
    This mutates grove_notice_viewed_at server-side.
    """
    try:
        auth_headers = _get_auth_headers()
        if auth_headers.get("error"):
            raise Exception(f"Failed to get auth headers: {auth_headers['error']}")

        config = _get_oauth_config()
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{config['BASE_API_URL']}/api/oauth/account/grove_notice_viewed",
                headers={
                    **auth_headers.get("headers", {}),
                    "User-Agent": _get_claude_code_user_agent(),
                },
            )
        
        # Invalidate memoized settings so post-toggle reads are fresh
        mark_grove_settings_cache_dirty()
    except Exception as err:
        _log_error(err)


async def update_grove_settings(grove_enabled: bool) -> None:
    """
    Update Grove settings for the user account.
    Invalidates memoized settings so post-toggle confirmation picks up new value.
    """
    try:
        auth_headers = _get_auth_headers()
        if auth_headers.get("error"):
            raise Exception(f"Failed to get auth headers: {auth_headers['error']}")

        config = _get_oauth_config()
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.patch(
                f"{config['BASE_API_URL']}/api/oauth/account/settings",
                json={"grove_enabled": grove_enabled},
                headers={
                    **auth_headers.get("headers", {}),
                    "User-Agent": _get_claude_code_user_agent(),
                },
            )
        
        # Invalidate memoized settings
        mark_grove_settings_cache_dirty()
    except Exception as err:
        _log_error(err)


async def is_qualified_for_grove() -> bool:
    """
    Check if user is qualified for Grove (non-blocking, cache-first).
    
    This function never blocks on network - it returns cached data immediately
    and fetches in the background if needed. On cold start (no cache), it returns
    false and the Grove dialog won't show until the next session.
    """
    if not _is_consumer_subscriber():
        return False

    account_info = _get_oauth_account_info()
    account_id = account_info.get("account_uuid") if account_info else None
    if not account_id:
        return False

    global_config = _get_global_config()
    cached_entry = global_config.get("groveConfigCache", {}).get(account_id)
    now = time.time() * 1000

    # No cache - trigger background fetch and return false (non-blocking)
    if not cached_entry:
        _log_for_debugging(
            "Grove: No cache, fetching config in background (dialog skipped this session)"
        )
        # Fire and forget background fetch
        _ = _fetch_and_store_grove_config(account_id)
        return False

    # Cache exists but is stale - return cached value and refresh in background
    if now - cached_entry.get("timestamp", 0) > GROVE_CACHE_EXPIRATION_MS:
        _log_for_debugging(
            "Grove: Cache stale, returning cached data and refreshing in background"
        )
        _ = _fetch_and_store_grove_config(account_id)
        return cached_entry.get("grove_enabled", False)

    # Cache is fresh - return it immediately
    _log_for_debugging("Grove: Using fresh cached config")
    return cached_entry.get("grove_enabled", False)


async def _fetch_and_store_grove_config(account_id: str) -> None:
    """
    Fetch Grove config from API and store in cache.
    """
    try:
        result = await get_grove_notice_config()
        if not result.get("success"):
            return
        
        grove_enabled = result.get("data", {}).get("grove_enabled", False)
        cached_entry = _get_global_config().get("groveConfigCache", {}).get(account_id)
        
        if (
            cached_entry and 
            cached_entry.get("grove_enabled") == grove_enabled and
            time.time() * 1000 - cached_entry.get("timestamp", 0) <= GROVE_CACHE_EXPIRATION_MS
        ):
            return
        
        # Save to global config
        current_config = _get_global_config()
        new_cache = {**(current_config.get("groveConfigCache", {})), account_id: {
            "grove_enabled": grove_enabled,
            "timestamp": time.time() * 1000,
        }}
        _save_global_config(lambda c: {**c, "groveConfigCache": new_cache})
    except Exception as err:
        _log_for_debugging(f"Grove: Failed to fetch and store config: {err}")


# Module-level cache for get_grove_notice_config
_grove_notice_config_cache: Optional[Dict[str, Any]] = None


async def _fetch_grove_notice_config_impl() -> Dict[str, Any]:
    """
    Internal implementation to fetch Grove notice config from API.
    Returns ApiResult to distinguish between API failure and success.
    """
    global _grove_notice_config_cache
    
    if _is_essential_traffic_only():
        return {"success": False}

    try:
        auth_headers = _get_auth_headers()
        if auth_headers.get("error"):
            raise Exception(f"Failed to get auth headers: {auth_headers['error']}")

        config = _get_oauth_config()
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(
                f"{config['BASE_API_URL']}/api/claude_code_grove",
                headers={
                    **auth_headers.get("headers", {}),
                    "User-Agent": _get_user_agent(),
                },
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": {
                        "grove_enabled": data.get("grove_enabled", False),
                        "domain_excluded": data.get("domain_excluded", False),
                        "notice_is_grace_period": data.get("notice_is_grace_period", True),
                        "notice_reminder_frequency": data.get("notice_reminder_frequency"),
                    },
                }
            else:
                _log_for_debugging(f"Failed to fetch Grove notice config: {response.status_code}")
                return {"success": False}
    except Exception as err:
        _log_for_debugging(f"Failed to fetch Grove notice config: {err}")
        return {"success": False}


async def get_grove_notice_config() -> Dict[str, Any]:
    """
    Get Grove Statsig configuration from the API.
    Returns ApiResult to distinguish between API failure and success.
    Uses memoization for the session.
    """
    global _grove_notice_config_cache
    
    if _grove_notice_config_cache is not None:
        return _grove_notice_config_cache
    
    result = await _fetch_grove_notice_config_impl()
    _grove_notice_config_cache = result
    return result


def calculate_should_show_grove(
    settings_result: Dict[str, Any],
    config_result: Dict[str, Any],
    show_if_already_viewed: bool,
) -> bool:
    """
    Determines whether the Grove dialog should be shown.
    Returns false if either API call failed (after retry) - we hide the dialog on API failure.
    """
    # Hide dialog on API failure (after retry)
    if not settings_result.get("success") or not config_result.get("success"):
        return False

    settings = settings_result.get("data", {})
    config = config_result.get("data", {})

    has_chosen = settings.get("grove_enabled") is not None
    if has_chosen:
        return False
    if show_if_already_viewed:
        return True
    if not config.get("notice_is_grace_period"):
        return True

    # Check if we need to remind the user
    reminder_frequency = config.get("notice_reminder_frequency")
    grove_notice_viewed_at = settings.get("grove_notice_viewed_at")
    
    if reminder_frequency is not None and grove_notice_viewed_at:
        try:
            viewed_time = time.mktime(time.strptime(grove_notice_viewed_at, "%Y-%m-%dT%H:%M:%S.%fZ"))
            days_since_viewed = (time.time() - viewed_time) / (24 * 60 * 60)
            return days_since_viewed >= reminder_frequency
        except (ValueError, TypeError):
            pass

    # Show if never viewed before
    return grove_notice_viewed_at is None or grove_notice_viewed_at == ""


async def check_grove_for_non_interactive() -> None:
    """
    Check Grove status for non-interactive sessions.
    Logs events and displays messages based on Grove configuration.
    """
    settings_result, config_result = await Promise.all([
        get_grove_settings(),
        get_grove_notice_config(),
    ])

    # Check if user hasn't made a choice yet (returns false on API failure)
    should_show_grove = calculate_should_show_grove(
        settings_result,
        config_result,
        False,
    )

    if should_show_grove:
        # shouldShowGrove is only true if both API calls succeeded
        config = config_result.get("data") if config_result.get("success") else None
        
        if config is None or config.get("notice_is_grace_period"):
            # Grace period is still active - show informational message and continue
            print(
                "\nAn update to our Consumer Terms and Privacy Policy will take effect on October 8, 2025. Run `claude` to review the updated terms.\n",
                flush=True,
            )
            await mark_grove_notice_viewed()
        else:
            # Grace period has ended - show error message
            print(
                "\n[ACTION REQUIRED] An update to our Consumer Terms and Privacy Policy has taken effect on October 8, 2025. You must run `claude` to review the updated terms.\n",
                flush=True,
            )
            # In production, would call gracefulShutdown(1)


# Polyfill for Promise.all since we're writing async Python
class Promise:
    @staticmethod
    async def all(promises):
        results = []
        for p in promises:
            results.append(await p)
        return results
