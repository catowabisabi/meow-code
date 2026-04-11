"""
OpenTelemetry LogRecordExporter for first-party event logging.

This module provides:
- OpenTelemetry-compatible LogRecordExporter interface
- Batch retry with quadratic backoff (500ms → 30s)
- File-based JSONL queuing for failed events
- Chunked event sending to /api/event_logging/batch

Export cycles are controlled by the caller (e.g., BatchLogRecordProcessor),
which triggers export() when either:
- Time interval elapses (default: 5 seconds via scheduledDelayMillis)
- Batch size is reached (default: 200 events via maxExportBatchSize)

This exporter adds resilience on top:
- Append-only log for failed events (concurrency-safe)
- Quadratic backoff retry for failed events, dropped after maxAttempts
- Immediate retry of queued events when any export succeeds
- Chunking large event sets into smaller batches
- Auth fallback: retries without auth on 401 errors
"""

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from typing import Any, Callable, List, Optional

from .growthbook import get_dynamic_config

logger = logging.getLogger(__name__)

# Unique ID for this process run - used to isolate failed event files between runs
BATCH_UUID = uuid.uuid4().hex

# File prefix for failed event storage
FILE_PREFIX = "1p_failed_events."

# Default values
DEFAULT_TIMEOUT_MS = 10000
DEFAULT_MAX_BATCH_SIZE = 200
DEFAULT_BASE_BACKOFF_DELAY_MS = 500
DEFAULT_MAX_BACKOFF_DELAY_MS = 30000
DEFAULT_MAX_ATTEMPTS = 8
DEFAULT_BATCH_DELAY_MS = 100


def _get_storage_dir() -> str:
    """Storage directory for failed events - evaluated at runtime to respect CLAUDE_CONFIG_DIR in tests."""
    config_dir = os.getenv("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
    return os.path.join(config_dir, "telemetry")


class ExportResultCode:
    """OpenTelemetry Export Result Codes."""
    SUCCESS = "success"
    FAILED = "failed"


class ExportResult:
    """Result of an export operation."""
    def __init__(self, code: str, error: Optional[Exception] = None):
        self.code = code
        self.error = error


class LogRecordExporter:
    """
    Interface for OpenTelemetry LogRecordExporter.
    
    Implementations should override the export method to send logs
    to their destination.
    """
    
    def export(
        self,
        logs: List[Any],
        result_callback: Callable[[ExportResult], None],
    ) -> None:
        """
        Export logs to destination.
        
        Args:
            logs: List of ReadableLogRecord objects
            result_callback: Callback to invoke when export completes
        """
        raise NotImplementedError


class FirstPartyEventLoggingExporter(LogRecordExporter):
    """
    Exporter for 1st-party event logging to /api/event_logging/batch.
    
    This exporter adds resilience:
    - Append-only log for failed events (concurrency-safe)
    - Quadratic backoff retry for failed events, dropped after maxAttempts
    - Immediate retry of queued events when any export succeeds
    - Chunking large event sets into smaller batches
    - Auth fallback: retries without auth on 401 errors
    """
    
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT_MS,
        max_batch_size: int = DEFAULT_MAX_BATCH_SIZE,
        skip_auth: bool = False,
        batch_delay_ms: int = DEFAULT_BATCH_DELAY_MS,
        base_backoff_delay_ms: int = DEFAULT_BASE_BACKOFF_DELAY_MS,
        max_backoff_delay_ms: int = DEFAULT_MAX_BACKOFF_DELAY_MS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        path: Optional[str] = None,
        base_url: Optional[str] = None,
        is_killed: Optional[Callable[[], bool]] = None,
        schedule: Optional[Callable[[Callable[[], None], int], Callable[[], None]]] = None,
    ):
        """
        Initialize the exporter.
        
        Args:
            timeout: Request timeout in milliseconds
            max_batch_size: Maximum events per batch
            skip_auth: Skip authentication
            batch_delay_ms: Delay between batches in milliseconds
            base_backoff_delay_ms: Base backoff delay in milliseconds
            max_backoff_delay_ms: Maximum backoff delay in milliseconds
            max_attempts: Maximum retry attempts
            path: API path (default: /api/event_logging/batch)
            base_url: Base URL for API
            is_killed: Callback to check if killswitch is active
            schedule: Custom scheduler function
        """
        # Default: prod, except when ANTHROPIC_BASE_URL is explicitly staging.
        # Overridable via tengu_1p_event_batch_config.baseUrl.
        if base_url and "staging" in base_url:
            self._base_url = base_url
        elif os.getenv("ANTHROPIC_BASE_URL") == "https://api-staging.anthropic.com":
            self._base_url = "https://api-staging.anthropic.com"
        else:
            self._base_url = base_url or "https://api.anthropic.com"
        
        self._endpoint = f"{self._base_url}{path or '/api/event_logging/batch'}"
        self._timeout = timeout
        self._max_batch_size = max_batch_size
        self._skip_auth = skip_auth
        self._batch_delay_ms = batch_delay_ms
        self._base_backoff_delay_ms = base_backoff_delay_ms
        self._max_backoff_delay_ms = max_backoff_delay_ms
        self._max_attempts = max_attempts
        self._is_killed = is_killed or (lambda: False)
        
        if schedule:
            self._schedule = schedule
        else:
            self._schedule = self._default_schedule
        
        self._pending_exports: List[asyncio.Task[None]] = []
        self._is_shutdown = False
        self._cancel_backoff: Optional[Callable[[], None]] = None
        self._attempts = 0
        self._is_retrying = False
        self._last_export_error_context: Optional[str] = None
        
        # Retry any failed events from previous runs of this session (in background)
        asyncio.create_task(self._retry_previous_batches())
    
    def _default_schedule(self, fn: Callable[[], None], delay_ms: int) -> Callable[[], None]:
        """Default scheduler using asyncio."""
        async def wrapper():
            await asyncio.sleep(delay_ms / 1000)
            fn()
        
        handle = asyncio.create_task(wrapper())
        
        def cancel():
            if not handle.done():
                handle.cancel()
        
        return cancel
    
    def _get_session_id(self) -> str:
        """Get current session ID."""
        try:
            from .metadata import get_session_id
            return get_session_id()
        except Exception:
            return "unknown"
    
    # --- Storage helpers ---
    
    def _get_current_batch_file_path(self) -> str:
        """Get the file path for the current batch."""
        return os.path.join(
            _get_storage_dir(),
            f"{FILE_PREFIX}{self._get_session_id()}.{BATCH_UUID}.json",
        )
    
    async def _load_events_from_file(self, file_path: str) -> List[dict]:
        """Load events from a JSONL file."""
        try:
            if not os.path.exists(file_path):
                return []
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            events = []
            for line in lines:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
            return events
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from {file_path}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Failed to load events from {file_path}: {e}")
            return []
    
    async def _load_events_from_current_batch(self) -> List[dict]:
        """Load events from the current batch file."""
        return await self._load_events_from_file(self._get_current_batch_file_path())
    
    async def _save_events_to_file(self, file_path: str, events: List[dict]) -> None:
        """Save events to a JSONL file."""
        try:
            if not events:
                try:
                    os.unlink(file_path)
                except FileNotFoundError:
                    pass
                return
            
            # Ensure storage directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write as JSON lines (one event per line)
            with open(file_path, "w", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to save events to {file_path}: {e}")
    
    async def _append_events_to_file(self, file_path: str, events: List[dict]) -> None:
        """Append events to a JSONL file (atomic on most filesystems)."""
        if not events:
            return
        try:
            # Ensure storage directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Append as JSON lines (one event per line)
            with open(file_path, "a", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to append events to {file_path}: {e}")
    
    async def _delete_file(self, file_path: str) -> None:
        """Delete a file, ignoring errors."""
        try:
            os.unlink(file_path)
        except FileNotFoundError:
            pass
        except Exception:
            pass
    
    # --- Previous batch retry (startup) ---
    
    async def _retry_previous_batches(self) -> None:
        """Retry failed events from previous runs."""
        try:
            storage_dir = _get_storage_dir()
            if not os.path.exists(storage_dir):
                return
            
            prefix = f"{FILE_PREFIX}{self._get_session_id()}."
            for filename in os.listdir(storage_dir):
                if filename.startswith(prefix) and filename.endswith(".json") and BATCH_UUID not in filename:
                    file_path = os.path.join(storage_dir, filename)
                    asyncio.create_task(self._retry_file_in_background(file_path))
        except Exception as e:
            logger.error(f"Failed to retry previous batches: {e}")
    
    async def _retry_file_in_background(self, file_path: str) -> None:
        """Retry a single file in the background."""
        if self._attempts >= self._max_attempts:
            await self._delete_file(file_path)
            return
        
        events = await self._load_events_from_file(file_path)
        if not events:
            await self._delete_file(file_path)
            return
        
        if os.getenv("USER_TYPE") == "ant":
            logger.debug(f"1P event logging: retrying {len(events)} events from previous batch")
        
        failed_events = await self._send_events_in_batches(events)
        if not failed_events:
            await self._delete_file(file_path)
            if os.getenv("USER_TYPE") == "ant":
                logger.debug("1P event logging: previous batch retry succeeded")
        else:
            # Save only the failed events back
            await self._save_events_to_file(file_path, failed_events)
            if os.getenv("USER_TYPE") == "ant":
                logger.debug(f"1P event logging: previous batch retry failed, {len(failed_events)} events remain")
    
    # --- Main export interface ---
    
    def export(
        self,
        logs: List[Any],
        result_callback: Callable[[ExportResult], None],
    ) -> None:
        """Export logs (OpenTelemetry LogRecordExporter interface)."""
        if self._is_shutdown:
            if os.getenv("USER_TYPE") == "ant":
                logger.debug("1P event logging export failed: Exporter has been shutdown")
            result_callback(ExportResult(
                code=ExportResultCode.FAILED,
                error=Exception("Exporter has been shutdown"),
            ))
            return
        
        export_promise = asyncio.create_task(self._do_export(logs, result_callback))
        self._pending_exports.append(export_promise)
        
        # Clean up completed exports
        export_promise.add_done_callback(
            lambda t: self._pending_exports.remove(t) if t in self._pending_exports else None
        )
    
    async def _do_export(
        self,
        logs: List[Any],
        result_callback: Callable[[ExportResult], None],
    ) -> None:
        """Internal export implementation."""
        try:
            # Filter for event logs only (by scope name)
            event_logs = [
                log for log in logs
                if self._get_instrumentation_scope_name(log) == "com.anthropic.claude_code.events"
            ]
            
            if not event_logs:
                result_callback(ExportResult(code=ExportResultCode.SUCCESS))
                return
            
            # Transform new logs
            events = self._transform_logs_to_events(event_logs)
            
            if not events:
                result_callback(ExportResult(code=ExportResultCode.SUCCESS))
                return
            
            if self._attempts >= self._max_attempts:
                result_callback(ExportResult(
                    code=ExportResultCode.FAILED,
                    error=Exception(f"Dropped {len(events)} events: max attempts ({self._max_attempts}) reached"),
                ))
                return
            
            # Send events
            failed_events = await self._send_events_in_batches(events)
            self._attempts += 1
            
            if failed_events:
                await self._queue_failed_events(failed_events)
                self._schedule_backoff_retry()
                context = f" ({self._last_export_error_context})" if self._last_export_error_context else ""
                result_callback(ExportResult(
                    code=ExportResultCode.FAILED,
                    error=Exception(f"Failed to export {len(failed_events)} events{context}"),
                ))
                return
            
            # Success - reset backoff and immediately retry any queued events
            self._reset_backoff()
            queued_count = await self._get_queued_event_count()
            if queued_count > 0 and not self._is_retrying:
                asyncio.create_task(self._retry_failed_events())
            
            result_callback(ExportResult(code=ExportResultCode.SUCCESS))
            
        except Exception as e:
            if os.getenv("USER_TYPE") == "ant":
                logger.debug(f"1P event logging export failed: {e}")
            logger.error(f"1P event logging export error: {e}")
            result_callback(ExportResult(
                code=ExportResultCode.FAILED,
                error=e,
            ))
    
    def _get_instrumentation_scope_name(self, log: Any) -> Optional[str]:
        """Get instrumentation scope name from a log record."""
        if hasattr(log, "instrumentation_scope") and log.instrumentation_scope:
            return log.instrumentation_scope.name if hasattr(log.instrumentation_scope, "name") else None
        if isinstance(log, dict):
            scope = log.get("instrumentationScope") or log.get("instrumentation_scope")
            if scope:
                return scope.name if hasattr(scope, "name") else scope.get("name")
        return None
    
    def _get_attributes(self, log: Any) -> dict:
        """Get attributes from a log record."""
        if hasattr(log, "attributes"):
            attrs = log.attributes
            if isinstance(attrs, dict):
                return attrs
        if isinstance(log, dict):
            return log.get("attributes", {})
        return {}
    
    def _get_body(self, log: Any) -> str:
        """Get body from a log record."""
        if hasattr(log, "body"):
            return str(log.body) if log.body is not None else ""
        if isinstance(log, dict):
            return str(log.get("body", ""))
        return ""
    
    def _get_hr_time(self, log: Any) -> tuple:
        """Get hrTime (high-resolution time) from a log record."""
        if hasattr(log, "hrTime"):
            hr_time = log.hrTime
            if isinstance(hr_time, (list, tuple)) and len(hr_time) >= 2:
                return (hr_time[0], hr_time[1])
            return (int(time.time()), 0)
        if isinstance(log, dict):
            hr_time = log.get("hrTime") or log.get("hr_time")
            if isinstance(hr_time, (list, tuple)) and len(hr_time) >= 2:
                return (hr_time[0], hr_time[1])
        return (int(time.time()), 0)
    
    async def _send_events_in_batches(self, events: List[dict]) -> List[dict]:
        """Send events in batches, with short-circuit on failure."""
        # Chunk events into batches
        batches = []
        for i in range(0, len(events), self._max_batch_size):
            batches.append(events[i:i + self._max_batch_size])
        
        if os.getenv("USER_TYPE") == "ant":
            logger.debug(f"1P event logging: exporting {len(events)} events in {len(batches)} batch(es)")
        
        # Send each batch with delay between them. On first failure, short-circuit.
        failed_batch_events: List[dict] = []
        last_error_context: Optional[str] = None
        
        for i, batch in enumerate(batches):
            try:
                await self._send_batch_with_retry({"events": batch})
            except Exception as e:
                last_error_context = self._get_error_context(e)
                for j in range(i, len(batches)):
                    failed_batch_events.extend(batches[j])
                if os.getenv("USER_TYPE") == "ant":
                    skipped = len(batches) - 1 - i
                    logger.debug(
                        f"1P event logging: batch {i + 1}/{len(batches)} failed ({last_error_context}); "
                        f"short-circuiting {skipped} remaining batch(es)"
                    )
                break
            
            if i < len(batches) - 1 and self._batch_delay_ms > 0:
                await asyncio.sleep(self._batch_delay_ms / 1000)
        
        if failed_batch_events and last_error_context:
            self._last_export_error_context = last_error_context
        
        return failed_batch_events
    
    def _get_error_context(self, error: Exception) -> str:
        """Get a human-readable error context string."""
        parts = []
        
        # Try to get request-id from error
        if hasattr(error, "response") and error.response is not None:
            headers = getattr(error.response, "headers", {}) or {}
            request_id = headers.get("request-id") if isinstance(headers, dict) else getattr(headers, "get", lambda x: None)("request-id")
            if request_id:
                parts.append(f"request-id={request_id}")
            
            status = getattr(error.response, "status", None)
            if status:
                parts.append(f"status={status}")
        
        if hasattr(error, "code") and error.code:
            parts.append(f"code={error.code}")
        
        if str(error):
            parts.append(str(error))
        
        return ", ".join(parts) if parts else str(error)
    
    async def _queue_failed_events(self, events: List[dict]) -> None:
        """Queue failed events to disk for later retry."""
        file_path = self._get_current_batch_file_path()
        await self._append_events_to_file(file_path, events)
        
        context = f" ({self._last_export_error_context})" if self._last_export_error_context else ""
        logger.error(f"1P event logging: {len(events)} events failed to export{context}")
    
    def _schedule_backoff_retry(self) -> None:
        """Schedule a backoff retry with quadratic delay."""
        # Don't schedule if already retrying or shutdown
        if self._cancel_backoff or self._is_retrying or self._is_shutdown:
            return
        
        # Quadratic backoff (matching Statsig SDK): base * attempts²
        delay = min(
            self._base_backoff_delay_ms * self._attempts * self._attempts,
            self._max_backoff_delay_ms,
        )
        
        if os.getenv("USER_TYPE") == "ant":
            logger.debug(f"1P event logging: scheduling backoff retry in {delay}ms (attempt {self._attempts})")
        
        def callback():
            self._cancel_backoff = None
            asyncio.create_task(self._retry_failed_events())
        
        self._cancel_backoff = self._schedule(callback, delay / 1000)
    
    async def _retry_failed_events(self) -> None:
        """Retry failed events from the current batch file."""
        file_path = self._get_current_batch_file_path()
        
        # Keep retrying while there are events and endpoint is healthy
        while not self._is_shutdown:
            events = await self._load_events_from_file(file_path)
            if not events:
                break
            
            if self._attempts >= self._max_attempts:
                if os.getenv("USER_TYPE") == "ant":
                    logger.debug(f"1P event logging: max attempts ({self._max_attempts}) reached, dropping {len(events)} events")
                await self._delete_file(file_path)
                self._reset_backoff()
                return
            
            self._is_retrying = True
            
            # Clear file before retry (we have events in memory now)
            await self._delete_file(file_path)
            
            if os.getenv("USER_TYPE") == "ant":
                logger.debug(f"1P event logging: retrying {len(events)} failed events (attempt {self._attempts + 1})")
            
            failed_events = await self._send_events_in_batches(events)
            self._attempts += 1
            
            self._is_retrying = False
            
            if failed_events:
                # Write failures back to disk
                await self._save_events_to_file(file_path, failed_events)
                self._schedule_backoff_retry()
                return  # Failed - wait for backoff
            
            # Success - reset backoff and continue loop to drain any newly queued events
            self._reset_backoff()
            if os.getenv("USER_TYPE") == "ant":
                logger.debug("1P event logging: backoff retry succeeded")
    
    def _reset_backoff(self) -> None:
        """Reset backoff state."""
        self._attempts = 0
        if self._cancel_backoff:
            self._cancel_backoff()
            self._cancel_backoff = None
    
    async def _send_batch_with_retry(self, payload: dict) -> None:
        """Send a batch of events to the API endpoint."""
        if self._is_killed():
            # Throw so the caller short-circuits remaining batches and queues
            # everything to disk. Zero network traffic while killed; the backoff
            # timer keeps ticking and will resume POSTs as soon as the GrowthBook
            # cache picks up the cleared flag.
            raise Exception("firstParty sink killswitch active")
        
        base_headers = {
            "Content-Type": "application/json",
            "User-Agent": "claude-code",
            "x-service-name": "claude-code",
        }
        
        # Check trust status - skip auth if trust hasn't been established yet
        has_trust = self._check_has_trust()
        should_skip_auth = self._skip_auth or not has_trust
        
        if not should_skip_auth:
            # Check if OAuth token is expired or lacks profile scope
            tokens = self._get_oauth_tokens()
            if tokens:
                if not self._has_profile_scope():
                    should_skip_auth = True
                elif self._is_oauth_token_expired(tokens):
                    should_skip_auth = True
                    if os.getenv("USER_TYPE") == "ant":
                        logger.debug("1P event logging: OAuth token expired, skipping auth to avoid 401")
        
        # Get auth headers if needed
        auth_headers = {}
        use_auth = False
        if not should_skip_auth:
            auth_result = self._get_auth_headers()
            if not auth_result.get("error"):
                auth_headers = auth_result.get("headers", {})
                use_auth = True
        
        if not use_auth and os.getenv("USER_TYPE") == "ant":
            logger.debug("1P event logging: auth not available, sending without auth")
        
        headers = {**base_headers, **auth_headers}
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=self._timeout / 1000) as client:
                response = await client.post(self._endpoint, json=payload, headers=headers)
                response.raise_for_status()
                self._log_success(len(payload.get("events", [])), use_auth, response.text)
                return
        except httpx.HTTPStatusError as e:
            # Handle 401 by retrying without auth
            if use_auth and e.response.status_code == 401:
                if os.getenv("USER_TYPE") == "ant":
                    logger.debug("1P event logging: 401 auth error, retrying without auth")
                async with httpx.AsyncClient(timeout=self._timeout / 1000) as client:
                    response = await client.post(self._endpoint, json=payload, headers=base_headers)
                    response.raise_for_status()
                    self._log_success(len(payload.get("events", [])), False, response.text)
                    return
            raise
        except Exception:
            raise
    
    def _check_has_trust(self) -> bool:
        """Check if trust dialog has been accepted."""
        try:
            from .config import check_has_trust_dialog_accepted
            return check_has_trust_dialog_accepted()
        except Exception:
            return False
    
    def _is_non_interactive_session(self) -> bool:
        """Check if session is non-interactive."""
        try:
            from .metadata import get_is_non_interactive_session
            return get_is_non_interactive_session()
        except Exception:
            return False
    
    def _get_oauth_tokens(self) -> Optional[dict]:
        """Get OAuth tokens if available."""
        try:
            from .auth import get_claude_ai_oauth_tokens
            return get_claude_ai_oauth_tokens()
        except Exception:
            return None
    
    def _has_profile_scope(self) -> bool:
        """Check if OAuth token has profile scope."""
        try:
            from .auth import has_profile_scope
            return has_profile_scope()
        except Exception:
            return False
    
    def _is_oauth_token_expired(self, tokens: dict) -> bool:
        """Check if OAuth token is expired."""
        try:
            from .auth import is_oauth_token_expired
            return is_oauth_token_expired(tokens.get("expires_at"))
        except Exception:
            return False
    
    def _get_auth_headers(self) -> dict:
        """Get authentication headers."""
        try:
            from .http import get_auth_headers
            return get_auth_headers()
        except Exception:
            return {"error": "unavailable"}
    
    def _log_success(self, event_count: int, with_auth: bool, response_data: Any) -> None:
        """Log successful export."""
        if os.getenv("USER_TYPE") == "ant":
            auth_str = " (with auth)" if with_auth else " (without auth)"
            logger.debug(f"1P event logging: {event_count} events exported successfully{auth_str}")
            logger.debug(f"API Response: {response_data}")
    
    def _hr_time_to_date(self, hr_time: tuple) -> time.datetime:
        """Convert hrTime tuple to datetime."""
        seconds, nanoseconds = hr_time
        return time.datetime.fromtimestamp(seconds + nanoseconds / 1_000_000_000)
    
    def _transform_logs_to_events(self, logs: List[Any]) -> List[dict]:
        """Transform log records to event format."""
        from .metadata import to_1p_event_format
        from .strip import strip_proto_fields
        
        events = []
        
        for log in logs:
            attributes = self._get_attributes(log)
            
            # Check if this is a GrowthBook experiment event
            if attributes.get("event_type") == "GrowthbookExperimentEvent":
                timestamp = self._hr_time_to_date(self._get_hr_time(log))
                account_uuid = attributes.get("account_uuid")
                organization_uuid = attributes.get("organization_uuid")
                
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
                        "session_id": attributes.get("session_id") or self._get_session_id(),
                        "auth": {"account_uuid": account_uuid, "organization_uuid": organization_uuid}
                            if account_uuid or organization_uuid else None,
                    },
                })
                continue
            
            # Extract event name
            event_name = attributes.get("event_name") or self._get_body(log) or "unknown"
            
            # Extract metadata objects
            core_metadata = attributes.get("core_metadata")
            user_metadata = attributes.get("user_metadata", {})
            event_metadata = attributes.get("event_metadata", {})
            
            if not core_metadata:
                # Emit partial event if core metadata is missing
                if os.getenv("USER_TYPE") == "ant":
                    logger.debug(f"1P event logging: core_metadata missing for event {event_name}")
                
                events.append({
                    "event_type": "ClaudeCodeInternalEvent",
                    "event_data": {
                        "event_id": attributes.get("event_id"),
                        "event_name": event_name,
                        "client_timestamp": self._hr_time_to_date(self._get_hr_time(log)).isoformat(),
                        "session_id": self._get_session_id(),
                        "additional_metadata": base64.b64encode(
                            json.dumps({"transform_error": "core_metadata attribute is missing"}).encode()
                        ).decode() if True else None,
                    },
                })
                continue
            
            # Transform to 1P format
            formatted = to_1p_event_format(core_metadata, user_metadata, event_metadata)
            
            # _PROTO_* keys are PII-tagged values meant only for privileged BQ columns.
            # Hoist known keys to proto fields, then defensively strip any remaining _PROTO_*.
            proto_keys = ["_PROTO_skill_name", "_PROTO_plugin_name", "_PROTO_marketplace_name"]
            additional = {k: v for k, v in formatted.get("additional", {}).items() if k not in proto_keys}
            additional = strip_proto_fields(additional)
            
            # Build event_data dict
            event_data = {
                "event_id": attributes.get("event_id"),
                "event_name": event_name,
                "client_timestamp": self._hr_time_to_date(self._get_hr_time(log)).isoformat(),
                "device_id": attributes.get("user_id"),
                "email": user_metadata.get("email") if isinstance(user_metadata, dict) else None,
                "auth": formatted.get("auth"),
                **formatted.get("core", {}),
                "env": formatted.get("env"),
                "process": formatted.get("process"),
            }
            
            # Add proto fields if present
            for proto_key in proto_keys:
                key_name = proto_key.replace("_PROTO_", "")
                if formatted.get("additional", {}).get(proto_key):
                    event_data[key_name] = formatted["additional"][proto_key]
            
            # Add additional_metadata if not empty
            if additional:
                event_data["additional_metadata"] = base64.b64encode(
                    json.dumps(additional).encode()
                ).decode()
            
            events.append({
                "event_type": "ClaudeCodeInternalEvent",
                "event_data": event_data,
            })
        
        return events
    
    async def _get_queued_event_count(self) -> int:
        """Get the number of events in the current batch queue."""
        return len(await self._load_events_from_current_batch())
    
    async def shutdown(self) -> None:
        """Shutdown the exporter."""
        self._is_shutdown = True
        self._reset_backoff()
        await self.force_flush()
        if os.getenv("USER_TYPE") == "ant":
            logger.debug("1P event logging exporter shutdown complete")
    
    async def force_flush(self) -> None:
        """Force flush pending exports."""
        if self._pending_exports:
            await asyncio.gather(*self._pending_exports, return_exceptions=True)
        if os.getenv("USER_TYPE") == "ant":
            logger.debug("1P event logging exporter flush complete")


def create_first_party_exporter(
    path: Optional[str] = None,
    base_url: Optional[str] = None,
) -> FirstPartyEventLoggingExporter:
    """
    Create a FirstPartyEventLoggingExporter with configuration from GrowthBook.
    
    Args:
        path: Override API path
        base_url: Override base URL
    
    Returns:
        Configured exporter instance
    """
    # Get configuration from GrowthBook
    batch_config = get_dynamic_config("tengu_1p_event_batch_config", {})
    
    if isinstance(batch_config, dict):
        timeout = batch_config.get("timeout") or DEFAULT_TIMEOUT_MS
        max_batch_size = batch_config.get("maxExportBatchSize") or DEFAULT_MAX_BATCH_SIZE
        skip_auth = batch_config.get("skipAuth", False)
        max_attempts = batch_config.get("maxAttempts") or DEFAULT_MAX_ATTEMPTS
        
        if not path:
            path = batch_config.get("path")
        if not base_url:
            base_url = batch_config.get("baseUrl")
    else:
        timeout = DEFAULT_TIMEOUT_MS
        max_batch_size = DEFAULT_MAX_BATCH_SIZE
        skip_auth = False
        max_attempts = DEFAULT_MAX_ATTEMPTS
    
    # Get killswitch check
    from .sink_killswitch import is_sink_killed
    
    return FirstPartyEventLoggingExporter(
        timeout=timeout,
        max_batch_size=max_batch_size,
        skip_auth=skip_auth,
        max_attempts=max_attempts,
        path=path,
        base_url=base_url,
        is_killed=lambda: is_sink_killed("firstParty"),
    )