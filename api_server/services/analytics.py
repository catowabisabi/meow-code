import asyncio
import logging
import os
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

TelemetryEventMetadata = dict[str, bool | int | float | None]

QueuedEvent = tuple[str, TelemetryEventMetadata, bool]


_event_queue: list[QueuedEvent] = []
_sink: Callable[[str, TelemetryEventMetadata], None] | None = None
_sink_async: Callable[[str, TelemetryEventMetadata], Awaitable[None]] | None = None


def attach_analytics_sink(
    log_event_fn: Callable[[str, TelemetryEventMetadata], None],
    log_event_async_fn: Callable[[str, TelemetryEventMetadata], Awaitable[None]],
) -> None:
    global _sink, _sink_async, _event_queue

    if _sink is not None:
        return

    _sink = log_event_fn
    _sink_async = log_event_async_fn

    if _event_queue:
        queued_events = list(_event_queue)
        _event_queue.clear()

        user_type = os.getenv("USER_TYPE")
        if user_type == "ant":
            logger.info(f"Analytics sink attached, draining {len(queued_events)} queued events")

        def drain_queue() -> None:
            for event_name, metadata, is_async in queued_events:
                if is_async and _sink_async:
                    _sink_async(event_name, metadata)
                elif _sink:
                    _sink(event_name, metadata)

        asyncio.create_task(_drain_queue_async(drain_queue))


async def _drain_queue_async(drain_fn: Callable[[], None]) -> None:
    drain_fn()


def log_event(
    event_name: str,
    metadata: TelemetryEventMetadata | None = None,
) -> None:
    if metadata is None:
        metadata = {}

    if _sink is None:
        _event_queue.append((event_name, metadata, False))
        return

    _sink(event_name, metadata)


async def log_event_async(
    event_name: str,
    metadata: TelemetryEventMetadata | None = None,
) -> None:
    if metadata is None:
        metadata = {}

    if _sink_async is None and _sink is None:
        _event_queue.append((event_name, metadata, True))
        return

    if _sink_async is not None:
        await _sink_async(event_name, metadata)
    elif _sink is not None:
        _sink(event_name, metadata)


def log_tool_use(
    tool_name: str,
    duration_ms: int,
    success: bool,
    error: str | None = None,
) -> None:
    metadata: TelemetryEventMetadata = {
        "toolName": tool_name,
        "durationMs": duration_ms,
        "success": success,
        **({"error": 1} if error else {}),
    }
    log_event("tengu_tool_use_success" if success else "tengu_tool_use_error", metadata)


def log_agent_spawn(
    agent_id: str,
    agent_type: str,
    model: str,
) -> None:
    metadata: TelemetryEventMetadata = {
        "agentId": agent_id,
        "agentType": agent_type,
        "model": model,
    }
    log_event("tengu_agent_spawn", metadata)


def log_session_start(
    session_id: str,
    model: str,
    tools: list[str],
) -> None:
    metadata: TelemetryEventMetadata = {
        "sessionId": session_id,
        "model": model,
        "toolCount": len(tools),
    }
    log_event("tengu_session_start", metadata)


def log_session_end(
    session_id: str,
    duration_ms: int,
    total_tokens: int,
) -> None:
    metadata: TelemetryEventMetadata = {
        "sessionId": session_id,
        "durationMs": duration_ms,
        "totalTokens": total_tokens,
    }
    log_event("tengu_session_end", metadata)


async def shutdown_analytics() -> None:
    try:
        from api_server.services.analytics.datadog import shutdown_datadog
        await shutdown_datadog()
    except Exception as e:
        logger.warning(f"Datadog shutdown failed: {e}")

    try:
        from api_server.services.analytics.first_party_logger import shutdown_1p_event_logging
        await shutdown_1p_event_logging()
    except Exception as e:
        logger.warning(f"1P event logging shutdown failed: {e}")