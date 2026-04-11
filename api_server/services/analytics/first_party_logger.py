"""
First-party event logger with OpenTelemetry-style exporter.

This module provides:
- Event logging to /api/event_logging/batch
- Retry with quadratic backoff
- Disk-backed failed event storage
"""

import os
import json
import time
import asyncio
import logging
import threading
import uuid
import datetime
from typing import Any, Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

FILE_PREFIX = "1p_failed_events"
BATCH_UUID = uuid.uuid4().hex

DEFAULT_LOGS_EXPORT_INTERVAL_MS = 10000
DEFAULT_MAX_EXPORT_BATCH_SIZE = 200
DEFAULT_MAX_QUEUE_SIZE = 8192
DEFAULT_BASE_BACKOFF_DELAY_MS = 500
DEFAULT_MAX_BACKOFF_DELAY_MS = 30000
DEFAULT_MAX_ATTEMPTS = 8


@dataclass
class BatchConfig:
    scheduled_delay_millis: Optional[int] = None
    max_export_batch_size: Optional[int] = None
    max_queue_size: Optional[int] = None
    skip_auth: Optional[bool] = None
    max_attempts: Optional[int] = None
    path: Optional[str] = None
    base_url: Optional[str] = None


def _get_storage_dir() -> str:
    config_dir = os.getenv("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
    return os.path.join(config_dir, "telemetry")


def _get_current_batch_file_path() -> str:
    from api_server.services.analytics.metadata import get_session_id

    session_id = get_session_id()
    return os.path.join(
        _get_storage_dir(),
        f"{FILE_PREFIX}.{session_id}.{BATCH_UUID}.json",
    )


class FirstPartyEventLoggingExporter:
    def __init__(
        self,
        timeout: int = 10000,
        max_batch_size: int = DEFAULT_MAX_EXPORT_BATCH_SIZE,
        skip_auth: bool = False,
        batch_delay_ms: int = 100,
        base_backoff_delay_ms: int = DEFAULT_BASE_BACKOFF_DELAY_MS,
        max_backoff_delay_ms: int = DEFAULT_MAX_BACKOFF_DELAY_MS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        path: Optional[str] = None,
        base_url: Optional[str] = None,
        is_killed: Optional[Callable[[], bool]] = None,
        schedule_fn: Optional[Callable[[Callable[[], None], int], Callable[[], None]]] = None,
    ):
        self.timeout = timeout
        self.max_batch_size = max_batch_size
        self.skip_auth = skip_auth
        self.batch_delay_ms = batch_delay_ms
        self.base_backoff_delay_ms = base_backoff_delay_ms
        self.max_backoff_delay_ms = max_backoff_delay_ms
        self.max_attempts = max_attempts
        self.is_killed = is_killed or (lambda: False)

        if base_url and "staging" in base_url:
            self.base_url = base_url
        else:
            self.base_url = base_url or os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

        self.endpoint = f"{self.base_url}{path or '/api/event_logging/batch'}"

        self._pending_exports: list[asyncio.Task[None]] = []
        self._is_shutdown = False
        self._cancel_backoff: Optional[Callable[[], None]] = None
        self._attempts = 0
        self._is_retrying = False
        self._last_export_error_context: Optional[str] = None

        if schedule_fn:
            self._schedule = schedule_fn
        else:
            self._schedule = lambda fn, ms: self._default_schedule(fn, ms)

        self._retry_previous_batches()

    def _default_schedule(self, fn: Callable[[], None], ms: int) -> Callable[[], None]:
        timer = threading.Timer(ms / 1000, fn)
        timer.daemon = True
        timer.start()
        return lambda: timer.cancel()

    def _get_session_id(self) -> str:
        try:
            from api_server.services.analytics.metadata import get_session_id
            return get_session_id()
        except Exception:
            return "unknown"

    async def _retry_previous_batches(self) -> None:
        try:
            storage_dir = _get_storage_dir()
            if not os.path.exists(storage_dir):
                return

            prefix = f"{FILE_PREFIX}.{self._get_session_id()}."
            for filename in os.listdir(storage_dir):
                if filename.startswith(prefix) and filename.endswith(".json") and BATCH_UUID not in filename:
                    file_path = os.path.join(storage_dir, filename)
                    asyncio.create_task(self._retry_file_background(file_path))
        except Exception as e:
            logger.warning(f"Failed to retry previous batches: {e}")

    async def _retry_file_background(self, file_path: str) -> None:
        events = await self._load_events_from_file(file_path)
        if not events:
            try:
                os.unlink(file_path)
            except Exception:
                pass
            return

        if self._attempts >= self.max_attempts:
            await self._delete_file(file_path)
            return

        failed = await self._send_events_in_batches(events)
        if not failed:
            await self._delete_file(file_path)
        else:
            await self._save_events_to_file(file_path, failed)

    async def export(
        self,
        logs: list[dict[str, Any]],
        result_callback: Callable[[dict[str, Any]], None],
    ) -> None:
        if self._is_shutdown:
            result_callback({"code": "failed", "error": "Exporter shutdown"})
            return

        export_task = asyncio.create_task(self._do_export(logs, result_callback))
        self._pending_exports.append(export_task)
        export_task.add_done_callback(
            lambda t: self._pending_exports.remove(t) if t in self._pending_exports else None
        )

    async def _do_export(
        self,
        logs: list[dict[str, Any]],
        result_callback: Callable[[dict[str, Any]], None],
    ) -> None:
        try:
            event_logs = [
                log for log in logs
                if log.get("instrumentationScope", {}).get("name") == "com.anthropic.claude_code.events"
            ]

            if not event_logs:
                result_callback({"code": "success"})
                return

            events = self._transform_logs_to_events(event_logs)

            if not events:
                result_callback({"code": "success"})
                return

            if self._attempts >= self.max_attempts:
                result_callback({
                    "code": "failed",
                    "error": f"Max attempts ({self.max_attempts}) reached",
                })
                return

            failed = await self._send_events_in_batches(events)
            self._attempts += 1

            if failed:
                await self._queue_failed_events(failed)
                self._schedule_backoff_retry()
                error_context = self._last_export_error_context or ""
                result_callback({
                    "code": "failed",
                    "error": f"Failed to export {len(failed)} events{error_context}",
                })
                return

            self._reset_backoff()
            queued_count = await self._get_queued_event_count()
            if queued_count > 0 and not self._is_retrying:
                asyncio.create_task(self._retry_failed_events())

            result_callback({"code": "success"})

        except Exception as e:
            logger.error(f"1P export error: {e}")
            result_callback({"code": "failed", "error": str(e)})

    async def _send_events_in_batches(
        self, events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        batches = []
        for i in range(0, len(events), self.max_batch_size):
            batches.append(events[i : i + self.max_batch_size])

        failed_batch_events = []
        last_error_context: Optional[str] = None

        for i, batch in enumerate(batches):
            try:
                await self._send_batch_with_retry({"events": batch})
            except Exception as e:
                last_error_context = str(e)
                for j in range(i, len(batches)):
                    failed_batch_events.extend(batches[j])
                break

            if i < len(batches) - 1 and self.batch_delay_ms > 0:
                await asyncio.sleep(self.batch_delay_ms / 1000)

        if failed_batch_events and last_error_context:
            self._last_export_error_context = last_error_context

        return failed_batch_events

    async def _send_batch_with_retry(self, payload: dict[str, Any]) -> None:
        if self.is_killed():
            raise Exception("firstParty sink killswitch active")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "claude-code",
            "x-service-name": "claude-code",
        }

        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout / 1000) as client:
                response = await client.post(self.endpoint, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                async with httpx.AsyncClient(timeout=self.timeout / 1000) as client:
                    response = await client.post(self.endpoint, json=payload, headers=headers)
                    response.raise_for_status()
            else:
                raise
        except Exception:
            raise

    def _schedule_backoff_retry(self) -> None:
        if self._cancel_backoff or self._is_retrying or self._is_shutdown:
            return

        delay = min(
            self.base_backoff_delay_ms * self._attempts * self._attempts,
            self.max_backoff_delay_ms,
        )

        def callback() -> None:
            self._cancel_backoff = None
            asyncio.create_task(self._retry_failed_events())

        self._cancel_backoff = self._schedule(callback, delay / 1000)

    async def _retry_failed_events(self) -> None:
        self._is_retrying = True

        while not self._is_shutdown:
            events = await self._load_events_from_current_batch()
            if not events:
                break

            if self._attempts >= self.max_attempts:
                await self._delete_file(_get_current_batch_file_path())
                self._reset_backoff()
                self._is_retrying = False
                return

            await self._delete_file(_get_current_batch_file_path())

            failed = await self._send_events_in_batches(events)
            self._attempts += 1

            if failed:
                await self._save_events_to_file(_get_current_batch_file_path(), failed)
                self._schedule_backoff_retry()
                self._is_retrying = False
                return

            self._reset_backoff()

        self._is_retrying = False

    def _reset_backoff(self) -> None:
        self._attempts = 0
        if self._cancel_backoff:
            self._cancel_backoff()
            self._cancel_backoff = None

    async def _queue_failed_events(self, events: list[dict[str, Any]]) -> None:
        file_path = _get_current_batch_file_path()
        await self._append_events_to_file(file_path, events)

    async def _load_events_from_file(self, file_path: str) -> list[dict[str, Any]]:
        try:
            if not os.path.exists(file_path):
                return []
            with open(file_path, "r") as f:
                lines = f.readlines()
            events = []
            for line in lines:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
            return events
        except Exception as e:
            logger.warning(f"Failed to load events from {file_path}: {e}")
            return []

    async def _load_events_from_current_batch(self) -> list[dict[str, Any]]:
        return await self._load_events_from_file(_get_current_batch_file_path())

    async def _save_events_to_file(self, file_path: str, events: list[dict[str, Any]]) -> None:
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to save events to {file_path}: {e}")

    async def _append_events_to_file(self, file_path: str, events: list[dict[str, Any]]) -> None:
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "a") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to append events to {file_path}: {e}")

    async def _delete_file(self, file_path: str) -> None:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception:
            pass

    async def _get_queued_event_count(self) -> int:
        return len(await self._load_events_from_current_batch())

    def _transform_logs_to_events(self, logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        events = []

        for log in logs:
            attributes = log.get("attributes", {})

            if attributes.get("event_type") == "GrowthbookExperimentEvent":
                from api_server.services.analytics.metadata import get_session_id

                timestamp = self._hr_time_to_date(log.get("hrTime", [0, 0]))
                events.append({
                    "event_type": "GrowthbookExperimentEvent",
                    "event_data": {
                        "event_id": attributes.get("event_id"),
                        "timestamp": timestamp.isoformat() if timestamp else None,
                        "experiment_id": attributes.get("experiment_id"),
                        "variation_id": attributes.get("variation_id"),
                        "environment": attributes.get("environment"),
                        "user_attributes": attributes.get("user_attributes"),
                        "experiment_metadata": attributes.get("experiment_metadata"),
                        "device_id": attributes.get("device_id"),
                        "session_id": attributes.get("session_id") or get_session_id(),
                    },
                })
                continue

            event_name = attributes.get("event_name") or log.get("body", "unknown")

            core_metadata = attributes.get("core_metadata", {})
            user_metadata = attributes.get("user_metadata", {})
            event_metadata = attributes.get("event_metadata", {})

            if not core_metadata:
                events.append({
                    "event_type": "ClaudeCodeInternalEvent",
                    "event_data": {
                        "event_id": attributes.get("event_id"),
                        "event_name": event_name,
                        "session_id": self._get_session_id(),
                    },
                })
                continue

            formatted = self._to_1p_event_format(core_metadata, user_metadata, event_metadata)

            proto_keys = ["_PROTO_skill_name", "_PROTO_plugin_name", "_PROTO_marketplace_name"]
            additional = {k: v for k, v in formatted.get("additional", {}).items() if k not in proto_keys}

            events.append({
                "event_type": "ClaudeCodeInternalEvent",
                "event_data": {
                    "event_id": attributes.get("event_id"),
                    "event_name": event_name,
                    "device_id": attributes.get("user_id"),
                    "email": user_metadata.get("email"),
                    "auth": formatted.get("auth"),
                    **formatted.get("core", {}),
                    "env": formatted.get("env"),
                    "process": formatted.get("process"),
                    "skill_name": formatted.get("additional", {}).get("_PROTO_skill_name"),
                    "plugin_name": formatted.get("additional", {}).get("_PROTO_plugin_name"),
                    "marketplace_name": formatted.get("additional", {}).get("_PROTO_marketplace_name"),
                    "additional_metadata": (
                        __import__("base64").b64encode(json.dumps(additional).encode()).decode()
                        if additional else None
                    ),
                },
            })

        return events

    def _hr_time_to_date(self, hr_time: list) -> Optional[datetime.datetime]:
        if hr_time and len(hr_time) >= 2:
            seconds, nanoseconds = hr_time[0], hr_time[1]
            return datetime.datetime.fromtimestamp(seconds + nanoseconds / 1_000_000_000)
        return None

    def _to_1p_event_format(
        self,
        core_metadata: dict[str, Any],
        user_metadata: dict[str, Any],
        event_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        env_context = core_metadata.get("envContext", {})
        process_metrics = core_metadata.get("processMetrics")

        env = {
            "platform": env_context.get("platform", "unknown"),
            "platform_raw": env_context.get("platformRaw", "unknown"),
            "arch": env_context.get("arch", "unknown"),
            "node_version": env_context.get("nodeVersion", "unknown"),
            "terminal": env_context.get("terminal") or "unknown",
            "package_managers": env_context.get("packageManagers", ""),
            "runtimes": env_context.get("runtimes", ""),
            "is_running_with_bun": env_context.get("isRunningWithBun", False),
            "is_ci": env_context.get("isCi", False),
            "is_claubbit": env_context.get("isClaubbit", False),
            "is_claude_code_remote": env_context.get("isClaudeCodeRemote", False),
            "is_local_agent_mode": env_context.get("isLocalAgentMode", False),
            "is_conductor": env_context.get("isConductor", False),
            "is_github_action": env_context.get("isGithubAction", False),
            "is_claude_code_action": env_context.get("isClaudeCodeAction", False),
            "is_claude_ai_auth": env_context.get("isClaudeAiAuth", False),
            "version": env_context.get("version", ""),
            "build_time": env_context.get("buildTime", ""),
            "deployment_environment": env_context.get("deploymentEnvironment", ""),
        }

        if env_context.get("remoteEnvironmentType"):
            env["remote_environment_type"] = env_context["remoteEnvironmentType"]
        if env_context.get("wslVersion"):
            env["wsl_version"] = env_context["wslVersion"]
        if env_context.get("linuxDistroId"):
            env["linux_distro_id"] = env_context["linuxDistroId"]
        if env_context.get("vcs"):
            env["vcs"] = env_context["vcs"]
        if env_context.get("versionBase"):
            env["version_base"] = env_context["versionBase"]

        core = {
            "session_id": core_metadata.get("sessionId", ""),
            "model": core_metadata.get("model", ""),
            "user_type": core_metadata.get("userType", ""),
            "is_interactive": core_metadata.get("isInteractive", "false") == "true",
            "client_type": core_metadata.get("clientType", ""),
        }

        if core_metadata.get("betas"):
            core["betas"] = core_metadata["betas"]
        if core_metadata.get("subscriptionType"):
            core["subscription_type"] = core_metadata["subscriptionType"]

        auth = None
        if user_metadata.get("accountUuid") or user_metadata.get("organizationUuid"):
            auth = {
                "account_uuid": user_metadata.get("accountUuid"),
                "organization_uuid": user_metadata.get("organizationUuid"),
            }

        rh = event_metadata.get("rh")
        kairos_active = event_metadata.get("kairosActive")
        skill_mode = event_metadata.get("skillMode")
        observer_mode = event_metadata.get("observerMode")

        additional = {k: v for k, v in event_metadata.items() if v is not None}

        result: dict[str, Any] = {"env": env, "core": core}
        if auth:
            result["auth"] = auth
        if process_metrics:
            result["process"] = __import__("base64").b64encode(json.dumps(process_metrics).encode()).decode()
        if rh:
            additional["rh"] = rh
        if kairos_active:
            additional["is_assistant_mode"] = True
        if skill_mode:
            additional["skill_mode"] = skill_mode
        if observer_mode:
            additional["observer_mode"] = observer_mode
        result["additional"] = additional

        return result

    async def shutdown(self) -> None:
        self._is_shutdown = True
        self._reset_backoff()
        await self.force_flush()

    async def force_flush(self) -> None:
        if self._pending_exports:
            await asyncio.gather(*self._pending_exports, return_exceptions=True)


_first_party_logger: Optional[FirstPartyEventLoggingExporter] = None


def is_1p_event_logging_enabled() -> bool:
    try:
        from api_server.services.analytics.config import is_analytics_disabled
        return not is_analytics_disabled()
    except Exception:
        return False


def log_event_to_1p(
    event_name: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not is_1p_event_logging_enabled():
        return

    if _first_party_logger is None:
        return

    event_id = uuid.uuid4().hex
    event_record = {
        "body": event_name,
        "attributes": {
            "event_name": event_name,
            "event_id": event_id,
            "core_metadata": metadata.get("core_metadata", {}) if metadata else {},
            "user_metadata": metadata.get("user_metadata", {}) if metadata else {},
            "event_metadata": metadata.get("event_metadata", metadata) if metadata else {},
        },
        "hrTime": [int(time.time()), 0],
        "instrumentationScope": {"name": "com.anthropic.claude_code.events"},
    }

    def callback(result: dict[str, Any]) -> None:
        if result.get("code") == "failed":
            logger.warning(f"1P event export failed: {result.get('error')}")

    asyncio.create_task(_first_party_logger.export([event_record], callback))


async def shutdown_1p_event_logging() -> None:
    global _first_party_logger

    if _first_party_logger:
        await _first_party_logger.shutdown()
        _first_party_logger = None


def initialize_1p_event_logging() -> None:
    global _first_party_logger

    if not is_1p_event_logging_enabled():
        return

    try:
        from api_server.services.analytics.growthbook import get_dynamic_config

        batch_config_dict = get_dynamic_config(
            "tengu_1p_event_batch_config",
            {},
        )

        if isinstance(batch_config_dict, dict):
            batch_config = BatchConfig(
                scheduled_delay_millis=batch_config_dict.get("scheduledDelayMillis"),
                max_export_batch_size=batch_config_dict.get("maxExportBatchSize"),
                max_queue_size=batch_config_dict.get("maxQueueSize"),
                skip_auth=batch_config_dict.get("skipAuth"),
                max_attempts=batch_config_dict.get("maxAttempts"),
                path=batch_config_dict.get("path"),
                base_url=batch_config_dict.get("baseUrl"),
            )
        else:
            batch_config = BatchConfig()

        _first_party_logger = FirstPartyEventLoggingExporter(
            max_batch_size=batch_config.max_export_batch_size or DEFAULT_MAX_EXPORT_BATCH_SIZE,
            skip_auth=batch_config.skip_auth or False,
            max_attempts=batch_config.max_attempts or DEFAULT_MAX_ATTEMPTS,
            path=batch_config.path,
            base_url=batch_config.base_url,
            is_killed=lambda: _is_sink_killed("firstParty"),
        )

    except Exception as e:
        logger.error(f"Failed to initialize 1P event logging: {e}")


def _is_sink_killed(sink: str) -> bool:
    try:
        from api_server.services.analytics.growthbook import get_dynamic_config

        config = get_dynamic_config("tengu_frond_boric", {})
        return config.get(sink) is True
    except Exception:
        return False