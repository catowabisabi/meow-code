"""
Channel notifications for MCP servers.

Lets an MCP server push user messages into the conversation via
notifications/claude/channel notifications.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict


SAFE_META_KEY = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

CHANNEL_PERMISSION_METHOD = "notifications/claude/channel/permission"
CHANNEL_TAG = "channel"


class ChannelEntry(TypedDict):
    kind: str
    name: str
    marketplace: Optional[str]
    dev: bool


def get_allowed_channels() -> List[ChannelEntry]:
    """Get allowed channels from bootstrap state."""
    from .channel_allowlist import get_channel_allowlist
    return []


def get_channel_allowlist() -> List[Dict[str, str]]:
    """Get the channel allowlist."""
    return []


def is_channels_enabled() -> bool:
    """Check if channels feature is enabled."""
    return False


def wrap_channel_message(
    server_name: str,
    content: str,
    meta: Optional[Dict[str, str]] = None,
) -> str:
    """
    Wraps channel message content in XML tags.

    Args:
        server_name: Name of the MCP server
        content: Message content
        meta: Optional metadata dictionary

    Returns:
        XML-wrapped message string
    """
    attrs = ""
    if meta:
        for k, v in meta.items():
            if SAFE_META_KEY.match(k):
                safe_v = v.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
                attrs += f' {k}="{safe_v}"'

    return f'<{CHANNEL_TAG} source="{server_name.replace("&", "&amp;").replace('"', "&quot;")}"{attrs}>\n{content}\n</{CHANNEL_TAG}>'


class ChannelGateResult:
    """Result of channel gate check."""

    def __init__(
        self,
        action: str,
        kind: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        self.action = action
        self.kind = kind
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"action": self.action}
        if self.kind:
            result["kind"] = self.kind
        if self.reason:
            result["reason"] = self.reason
        return result


def find_channel_entry(
    server_name: str,
    channels: List[ChannelEntry],
) -> Optional[ChannelEntry]:
    """
    Find a channel entry matching the server name.

    Args:
        server_name: Name of the server
        channels: List of channel entries

    Returns:
        Matching entry or None
    """
    parts = server_name.split(":")
    for c in channels:
        if c["kind"] == "server":
            if server_name == c["name"]:
                return c
        elif parts[0] == "plugin" and len(parts) > 1 and parts[1] == c["name"]:
            return c
    return None


def gate_channel_server(
    server_name: str,
    capabilities: Optional[Dict[str, Any]] = None,
    plugin_source: Optional[str] = None,
) -> ChannelGateResult:
    """
    Gate an MCP server's channel notification path.

    Args:
        server_name: Name of the MCP server
        capabilities: Server capabilities
        plugin_source: Plugin source identifier

    Returns:
        ChannelGateResult with action and reason
    """
    if not capabilities:
        return ChannelGateResult("skip", "capability", "server missing capabilities")

    experimental = capabilities.get("experimental") or {}
    if not experimental.get("claude/channel"):
        return ChannelGateResult(
            "skip",
            "capability",
            "server did not declare claude/channel capability",
        )

    if not is_channels_enabled():
        return ChannelGateResult("skip", "disabled", "channels feature is not currently available")

    return ChannelGateResult("register")
