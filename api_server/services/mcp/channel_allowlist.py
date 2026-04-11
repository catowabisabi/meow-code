"""
Approved channel plugins allowlist.

The allowlist check is a pure {marketplace, plugin} comparison.
"""

from typing import Dict, List, Optional

from .channel_permissions import is_channel_permission_relay_enabled

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict


class ChannelAllowlistEntry(TypedDict):
    marketplace: str
    plugin: str


def _get_feature_value(feature_name: str, default: any = None) -> any:
    """Get feature value from GrowthBook."""
    return default


def get_channel_allowlist() -> List[ChannelAllowlistEntry]:
    """
    Get the channel allowlist from GrowthBook.

    Returns:
        List of allowed {marketplace, plugin} entries
    """
    raw = _get_feature_value("tengu_harbor_ledger", [])
    if isinstance(raw, list):
        return [ChannelAllowlistEntry(**item) for item in raw if isinstance(item, dict)]
    return []


def is_channels_enabled() -> bool:
    """
    Overall channels on/off switch.

    Default False; GrowthBook 5-min refresh.
    """
    return _get_feature_value("tengu_harbor", False)


def is_channel_allowlisted(
    plugin_source: Optional[str],
) -> bool:
    """
    Pure allowlist check keyed off pluginSource.

    Args:
        plugin_source: Plugin source identifier (e.g., "slack@anthropic")

    Returns:
        True if plugin is in allowlist
    """
    if not plugin_source:
        return False

    if "@" not in plugin_source:
        return False

    parts = plugin_source.rsplit("@", 1)
    if len(parts) != 2:
        return False

    name, marketplace = parts
    allowlist = get_channel_allowlist()

    return any(
        entry["plugin"] == name and entry["marketplace"] == marketplace
        for entry in allowlist
    )
