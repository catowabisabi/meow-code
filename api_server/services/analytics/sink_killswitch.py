"""
GrowthBook-based killswitch for analytics sinks.

This module provides:
- Per-sink analytics killswitch based on GrowthBook configuration
- Supports datadog and firstParty sink toggles
- Fail-open: missing/malformed config = sink stays on
"""

from typing import Literal

from .growthbook import get_dynamic_config

SinkName = Literal["datadog", "firstParty"]

SINK_KILLSWITCH_CONFIG_NAME = "tengu_frond_boric"


def is_sink_killed(sink: SinkName) -> bool:
    """
    Check if a specific analytics sink is killed via GrowthBook config.
    
    The GrowthBook JSON config shape: { datadog?: boolean, firstParty?: boolean }
    A value of true for a key stops all dispatch to that sink.
    
    NOTE: Must NOT be called from inside is_1p_event_logging_enabled() -
    growthbook.py:is_growthbook_enabled() calls that, so a lookup here would recurse.
    Call at per-event dispatch sites instead.
    
    Args:
        sink: The sink name to check ('datadog' or 'firstParty')
    
    Returns:
        True if the sink is killed (disabled), False otherwise
    """
    config = get_dynamic_config(SINK_KILLSWITCH_CONFIG_NAME, {})
    
    if not isinstance(config, dict):
        return False
    
    return config.get(sink) is True


def is_datadog_killed() -> bool:
    """Check if the datadog sink is killed."""
    return is_sink_killed("datadog")


def is_first_party_killed() -> bool:
    """Check if the firstParty sink is killed."""
    return is_sink_killed("firstParty")