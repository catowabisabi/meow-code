"""
Channel permissions for MCP servers.

Provides permission prompts over channels (Telegram, iMessage, Discord).
"""

import json
import re
from typing import Any, Callable, Dict, List

PERMISSION_REPLY_RE = re.compile(r"^\s*(y|yes|n|no)\s+([a-km-z]{5})\s*$", re.IGNORECASE)

ID_ALPHABET = "abcdefghijkmnopqrstuvwxyz"

ID_AVOID_SUBSTRINGS = [
    "fuck", "shit", "cunt", "cock", "dick", "twat", "piss", "crap", "bitch",
    "whore", "ass", "tit", "cum", "fag", "dyke", "nig", "kike", "rape",
    "nazi", "damn", "poo", "pee", "wank", "anus",
]


def _hash_to_id(input_str: str) -> str:
    """FNV-1a hash to base-25 encode."""
    h = 0x811c9DC5
    for i in range(len(input_str)):
        h ^= ord(input_str[i])
        h = (h * 0x01000193) & 0xFFFFFFFF
    h = h & 0xFFFFFFFF

    result = ""
    for _ in range(5):
        result += ID_ALPHABET[h % 25]
        h = h // 25
    return result


def short_request_id(tool_use_id: str) -> str:
    """
    Generate short ID from toolUseID.

    Args:
        tool_use_id: Tool usage ID

    Returns:
        5-letter short ID
    """
    candidate = _hash_to_id(tool_use_id)
    for salt in range(10):
        if not any(bad in candidate for bad in ID_AVOID_SUBSTRINGS):
            return candidate
        candidate = _hash_to_id(f"{tool_use_id}:{salt}")
    return candidate


def truncate_for_preview(input_data: Any) -> str:
    """
    Truncate tool input to phone-sized preview.

    Args:
        input_data: Tool input data

    Returns:
        Truncated string (max 200 chars)
    """
    try:
        s = json.dumps(input_data)
        return s[:200] + "…" if len(s) > 200 else s
    except Exception:
        return "(unserializable)"


ChannelPermissionResponse = Dict[str, Any]


class ChannelPermissionCallbacks:
    """Callbacks for channel permission responses."""

    def __init__(self):
        self._pending: Dict[str, Callable[[ChannelPermissionResponse], None]] = {}

    def on_response(
        self,
        request_id: str,
        handler: Callable[[ChannelPermissionResponse], None],
    ) -> Callable[[], None]:
        """
        Register a resolver for a request ID.

        Returns unsubscribe function.
        """
        key = request_id.lower()
        self._pending[key] = handler

        def unsubscribe() -> None:
            self._pending.pop(key, None)

        return unsubscribe

    def resolve(
        self,
        request_id: str,
        behavior: str,
        from_server: str,
    ) -> bool:
        """
        Resolve a pending request from a structured channel event.

        Returns True if the ID was pending.
        """
        key = request_id.lower()
        resolver = self._pending.get(key)
        if not resolver:
            return False

        self._pending.pop(key, None)
        resolver({"behavior": behavior, "fromServer": from_server})
        return True


def create_channel_permission_callbacks() -> ChannelPermissionCallbacks:
    """Create channel permission callbacks."""
    return ChannelPermissionCallbacks()


def filter_permission_relay_clients(
    clients: List[Any],
    is_in_allowlist: Callable[[str], bool],
) -> List[Any]:
    """
    Filter MCP clients to those that can relay permission prompts.

    Args:
        clients: List of MCP clients
        is_in_allowlist: Function to check allowlist

    Returns:
        Filtered list of connected clients with permission relay capability
    """
    result = []
    for c in clients:
        if c.type != "connected":
            continue
        if not is_in_allowlist(c.name):
            continue

        caps = c.capabilities or {}
        experimental = caps.get("experimental") or {}
        if experimental.get("claude/channel") and experimental.get("claude/channel/permission"):
            result.append(c)

    return result


def is_channel_permission_relay_enabled() -> bool:
    """Check if channel permission relay is enabled."""
    return False
