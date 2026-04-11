"""
OAuth redirect port helpers for MCP authentication.
"""

import asyncio
import os
from typing import Optional

# Windows dynamic port range 49152-65535 is reserved
_REDIRECT_PORT_RANGE_WINDOWS = (39152, 49151)
_REDIRECT_PORT_RANGE_DEFAULT = (49152, 65535)
_REDIRECT_PORT_FALLBACK = 3118


def _get_platform() -> str:
    """Get the current platform."""
    return os.environ.get("PLATFORM", "windows" if os.name == "nt" else "linux")


def _get_redirect_port_range() -> tuple[int, int]:
    """Get the redirect port range for the current platform."""
    if _get_platform() == "windows":
        return _REDIRECT_PORT_RANGE_WINDOWS
    return _REDIRECT_PORT_RANGE_DEFAULT


def build_redirect_uri(port: Optional[int] = None) -> str:
    """
    Builds a redirect URI on localhost with the given port and a fixed `/callback` path.

    RFC 8252 Section 7.3 (OAuth for Native Apps): loopback redirect URIs match any
    port as long as the path matches.

    Args:
        port: The port number to use. Defaults to REDIRECT_PORT_FALLBACK.

    Returns:
        The redirect URI string.
    """
    port = port or _REDIRECT_PORT_FALLBACK
    return f"http://localhost:{port}/callback"


def _get_mcp_oauth_callback_port() -> Optional[int]:
    """Get the configured MCP OAuth callback port from environment."""
    port_str = os.environ.get("MCP_OAUTH_CALLBACK_PORT", "")
    if port_str:
        try:
            port = int(port_str)
            return port if port > 0 else None
        except ValueError:
            return None
    return None


async def find_available_port() -> int:
    """
    Finds an available port in the specified range for OAuth redirect.
    Uses random selection for better security.

    Returns:
        An available port number.

    Raises:
        Error: If no available ports are found.
    """
    # First, try the configured port if specified
    configured_port = _get_mcp_oauth_callback_port()
    if configured_port:
        return configured_port

    min_port, max_port = _get_redirect_port_range()
    port_range = max_port - min_port + 1
    max_attempts = min(port_range, 100)  # Don't try forever

    import random

    for _ in range(max_attempts):
        port = min_port + random.randint(0, port_range - 1)

        try:
            await asyncio.open_connection("127.0.0.1", port)
            # Port is in use
            continue
        except OSError:
            # Port is available
            return port

    # If random selection failed, try the fallback port
    try:
        await asyncio.open_connection("127.0.0.1", _REDIRECT_PORT_FALLBACK)
        # Fallback port also in use
        raise Error(f"No available ports for OAuth redirect")
    except OSError:
        return _REDIRECT_PORT_FALLBACK


class Error(Exception):
    """Error raised when no available ports are found."""
    pass
