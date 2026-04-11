"""
Analytics sink routing logic.

Routes events to Datadog and first-party logging based on:
- Event sampling configuration
- Sink killswitch settings
- Datadog gate feature flag
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

DATADOG_GATE_NAME = "tengu_log_datadog_events"

_is_datadog_gate_enabled: bool | None = None


def _is_sink_killed(sink: str) -> bool:
    try:
        from api_server.services.analytics.growthbook import get_feature_value

        config = get_feature_value("tengu_frond_boric", {})
        if isinstance(config, dict):
            return config.get(sink) is True
    except Exception:
        pass
    return False


def _should_track_datadog() -> bool:
    if _is_sink_killed("datadog"):
        return False

    global _is_datadog_gate_enabled
    if _is_datadog_gate_enabled is not None:
        return _is_datadog_gate_enabled

    try:
        from api_server.services.analytics.growthbook import get_feature_value

        _is_datadog_gate_enabled = get_feature_value(DATADOG_GATE_NAME, False)
        return _is_datadog_gate_enabled
    except Exception:
        return False


def _should_sample_event(event_name: str) -> int | None:
    try:
        from api_server.services.analytics.growthbook import get_dynamic_config

        config = get_dynamic_config("tengu_event_sampling_config", {})
        if isinstance(config, dict) and event_name in config:
            event_config = config[event_name]
            if isinstance(event_config, dict):
                sample_rate = event_config.get("sample_rate")
                if isinstance(sample_rate, (int, float)):
                    if sample_rate <= 0:
                        return 0
                    if sample_rate >= 1:
                        return None
                    import random
                    return sample_rate if random.random() < sample_rate else 0
    except Exception:
        pass
    return None


def _strip_proto_fields(metadata: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in metadata.items() if not k.startswith("_PROTO_")}


async def _track_datadog(event_name: str, metadata: dict[str, Any]) -> None:
    try:
        from api_server.services.analytics.datadog import track_datadog_event

        await track_datadog_event(event_name, metadata)
    except Exception as e:
        logger.error(f"Datadog tracking failed: {e}")


def _log_to_1p(event_name: str, metadata: dict[str, Any]) -> None:
    try:
        from api_server.services.analytics.first_party_logger import log_event_to_1p

        log_event_to_1p(event_name, metadata)
    except Exception as e:
        logger.error(f"1P logging failed: {e}")


def _log_event_impl(event_name: str, metadata: dict[str, Any]) -> None:
    sample_result = _should_sample_event(event_name)

    if sample_result == 0:
        return

    metadata_with_sample = (
        {**metadata, "sample_rate": sample_result}
        if sample_result is not None
        else metadata
    )

    if _should_track_datadog():
        stripped = _strip_proto_fields(metadata_with_sample)
        asyncio.create_task(_track_datadog(event_name, stripped))

    _log_to_1p(event_name, metadata_with_sample)


async def _log_event_async_impl(
    event_name: str,
    metadata: dict[str, Any],
) -> None:
    _log_event_impl(event_name, metadata)


def initialize_analytics_gates() -> None:
    global _is_datadog_gate_enabled

    try:
        from api_server.services.analytics.growthbook import get_feature_value

        _is_datadog_gate_enabled = get_feature_value(DATADOG_GATE_NAME, False)
    except Exception as e:
        logger.warning(f"Failed to initialize analytics gates: {e}")


def initialize_analytics_sink() -> None:
    from api_server.services.analytics import attach_analytics_sink

    attach_analytics_sink(
        log_event_fn=_log_event_impl,
        log_event_async_fn=_log_event_async_impl,
    )