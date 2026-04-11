"""
Datadog event tracking with batching support.

This module provides:
- Allowed events filtering
- Event batching (max 100 events, 15s flush)
- Event metadata enrichment
"""

import os
import re
import logging
import threading
import hashlib
from typing import Any, Optional

logger = logging.getLogger(__name__)

DATADOG_LOGS_ENDPOINT = "https://http-intake.logs.us5.datadoghq.com/api/v2/logs"
DATADOG_CLIENT_TOKEN = "pubbbf48e6d78dae54bceaa4acf463299bf"
DEFAULT_FLUSH_INTERVAL_MS = 15000
MAX_BATCH_SIZE = 100
NETWORK_TIMEOUT_MS = 5000

DATADOG_ALLOWED_EVENTS = {
    "chrome_bridge_connection_succeeded",
    "chrome_bridge_connection_failed",
    "chrome_bridge_disconnected",
    "chrome_bridge_tool_call_completed",
    "chrome_bridge_tool_call_error",
    "chrome_bridge_tool_call_started",
    "chrome_bridge_tool_call_timeout",
    "tengu_api_error",
    "tengu_api_success",
    "tengu_brief_mode_enabled",
    "tengu_brief_mode_toggled",
    "tengu_brief_send",
    "tengu_cancel",
    "tengu_compact_failed",
    "tengu_exit",
    "tengu_flicker",
    "tengu_init",
    "tengu_model_fallback_triggered",
    "tengu_oauth_error",
    "tengu_oauth_success",
    "tengu_oauth_token_refresh_failure",
    "tengu_oauth_token_refresh_success",
    "tengu_oauth_token_refresh_lock_acquiring",
    "tengu_oauth_token_refresh_lock_acquired",
    "tengu_oauth_token_refresh_starting",
    "tengu_oauth_token_refresh_completed",
    "tengu_oauth_token_refresh_lock_releasing",
    "tengu_oauth_token_refresh_lock_released",
    "tengu_query_error",
    "tengu_session_file_read",
    "tengu_started",
    "tengu_tool_use_error",
    "tengu_tool_use_granted_in_prompt_permanent",
    "tengu_tool_use_granted_in_prompt_temporary",
    "tengu_tool_use_rejected_in_prompt",
    "tengu_tool_use_success",
    "tengu_uncaught_exception",
    "tengu_unhandled_rejection",
    "tengu_voice_recording_started",
    "tengu_voice_toggled",
    "tengu_team_mem_sync_pull",
    "tengu_team_mem_sync_push",
    "tengu_team_mem_sync_started",
    "tengu_team_mem_entries_capped",
}

TAG_FIELDS = [
    "arch",
    "clientType",
    "errorType",
    "http_status_range",
    "http_status",
    "kairosActive",
    "model",
    "platform",
    "provider",
    "skillMode",
    "subscriptionType",
    "toolName",
    "userBucket",
    "userType",
    "version",
    "versionBase",
]

_log_batch: list[dict[str, Any]] = []
_flush_timer: Optional[threading.Timer] = None
_flush_lock = threading.Lock()
_datadog_initialized: Optional[bool] = None
_user_bucket: Optional[int] = None


def _camel_to_snake(s: str) -> str:
    result = []
    for i, c in enumerate(s):
        if c.isupper() and i > 0:
            result.append("_")
        result.append(c.lower())
    return "".join(result)


def _get_flush_interval_ms() -> int:
    env_val = os.getenv("DATADOG_FLUSH_INTERVAL_MS") or os.getenv("CLAUDE_CODE_DATADOG_FLUSH_INTERVAL_MS")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            pass
    return DEFAULT_FLUSH_INTERVAL_MS


def _get_user_bucket() -> int:
    global _user_bucket
    if _user_bucket is not None:
        return _user_bucket

    try:
        from api_server.services.analytics.metadata import get_or_create_user_id

        user_id = get_or_create_user_id()
        hash_val = hashlib.sha256(user_id.encode()).hexdigest()
        _user_bucket = int(hash_val[:8], 16) % 30
    except Exception:
        _user_bucket = 0

    return _user_bucket


async def _flush_logs() -> None:
    global _log_batch

    with _flush_lock:
        if not _log_batch:
            return
        logs_to_send = _log_batch
        _log_batch = []

    try:
        import httpx

        async with httpx.AsyncClient(timeout=NETWORK_TIMEOUT_MS / 1000) as client:
            await client.post(
                DATADOG_LOGS_ENDPOINT,
                json=logs_to_send,
                headers={
                    "Content-Type": "application/json",
                    "DD-API-KEY": DATADOG_CLIENT_TOKEN,
                },
            )
        logger.debug(f"Datadog: flushed {len(logs_to_send)} events")
    except Exception as e:
        logger.warning(f"Datadog flush failed: {e}")


def _schedule_flush() -> None:
    global _flush_timer

    with _flush_lock:
        if _flush_timer is not None:
            return

        interval = _get_flush_interval_ms()

        def timer_callback() -> None:
            global _flush_timer
            with _flush_lock:
                _flush_timer = None
            import asyncio
            asyncio.create_task(_flush_logs())

        _flush_timer = threading.Timer(interval / 1000, timer_callback)
        _flush_timer.daemon = True
        _flush_timer.start()


async def initialize_datadog() -> bool:
    global _datadog_initialized

    if _datadog_initialized is not None:
        return _datadog_initialized

    try:
        from api_server.services.analytics.config import is_analytics_disabled

        if is_analytics_disabled():
            _datadog_initialized = False
            return False

        _datadog_initialized = True
        return True
    except Exception as e:
        logger.error(f"Datadog initialization failed: {e}")
        _datadog_initialized = False
        return False


async def shutdown_datadog() -> None:
    global _flush_timer

    with _flush_lock:
        if _flush_timer is not None:
            _flush_timer.cancel()
            _flush_timer = None

    await _flush_logs()


async def track_datadog_event(
    event_name: str,
    properties: dict[str, Any],
) -> None:
    global _flush_timer

    if os.getenv("NODE_ENV") != "production":
        return

    try:
        from api_server.services.analytics.metadata import get_event_metadata

        initialized = await initialize_datadog()
        if not initialized or event_name not in DATADOG_ALLOWED_EVENTS:
            return

        metadata = await get_event_metadata(
            model=properties.get("model"),
            betas=properties.get("betas"),
        )

        all_data = {**metadata, **properties, "userBucket": _get_user_bucket()}

        tool_name = all_data.get("toolName")
        if isinstance(tool_name, str) and tool_name.startswith("mcp__"):
            all_data["toolName"] = "mcp"

        model = all_data.get("model")
        if isinstance(model, str) and os.getenv("USER_TYPE") != "ant":
            model_short = re.sub(r"\[1m]$", "", model)
            all_data["model"] = model_short

        version = all_data.get("version")
        if isinstance(version, str):
            version_match = re.match(
                r"^(\d+\.\d+\.\d+-dev\.\d{8})\.t\d+\.sha[a-f0-9]+$",
                version,
            )
            if version_match:
                all_data["version"] = version_match.group(1)

        status = all_data.pop("status", None)
        if status is not None:
            status_str = str(status)
            all_data["http_status"] = status_str
            if status_str and status_str[0] in "12345":
                all_data["http_status_range"] = f"{status_str[0]}xx"

        tags = [f"event:{event_name}"]
        for field in TAG_FIELDS:
            val = all_data.get(field)
            if val is not None:
                tags.append(f"{_camel_to_snake(field)}:{val}")

        log_entry = {
            "ddsource": "nodejs",
            "ddtags": ",".join(tags),
            "message": event_name,
            "service": "claude-code",
            "hostname": "claude-code",
            "env": os.getenv("USER_TYPE", "external"),
        }

        for key, val in all_data.items():
            if val is not None:
                log_entry[_camel_to_snake(key)] = val

        with _flush_lock:
            _log_batch.append(log_entry)

            if len(_log_batch) >= MAX_BATCH_SIZE:
                if _flush_timer:
                    _flush_timer.cancel()
                    _flush_timer = None
                import asyncio
                asyncio.create_task(_flush_logs())
            else:
                _schedule_flush()

    except Exception as e:
        logger.error(f"Datadog track failed: {e}")