"""
Analytics services package.

This package provides analytics event logging functionality with support for:
- GrowthBook feature flags with caching
- Datadog event tracking with batching
- First-party event logging with OpenTelemetry-style exporter

The main entry point is the analytics.py module which provides the event queue
and sink attachment logic.
"""

from .growthbook import (
    get_feature_value,
    get_dynamic_config,
    refresh_after_auth_change,
    on_growthbook_refresh,
)

from .first_party_logger import (
    is_1p_event_logging_enabled,
    log_event_to_1p,
    shutdown_1p_event_logging,
)

__all__ = [
    "get_feature_value",
    "get_dynamic_config",
    "refresh_after_auth_change",
    "on_growthbook_refresh",
    "is_1p_event_logging_enabled",
    "log_event_to_1p",
    "shutdown_1p_event_logging",
]


def log_event(event_name: str, **kwargs) -> None:
    pass