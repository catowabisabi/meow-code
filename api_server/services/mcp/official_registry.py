"""
Official MCP server registry utilities.

Provides functions to fetch and check official MCP server URLs.
"""

import os
from typing import Optional, Set

import httpx

# URLs stripped of query string and trailing slash — matches the normalization
# done by getLoggingSafeMcpBaseUrl so direct Set.has() lookup works.
_official_urls: Optional[Set[str]] = None

# Timeout for registry fetch in milliseconds
_FETCH_TIMEOUT_MS = 5000


def _normalize_url(url: str) -> Optional[str]:
    """
    Normalize a URL by removing query string and trailing slash.

    Args:
        url: The URL to normalize

    Returns:
        Normalized URL string or None if URL is invalid
    """
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        # Remove query string and trailing slash
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        return normalized
    except Exception:
        return None


async def prefetch_official_mcp_urls() -> None:
    """
    Fire-and-forget fetch of the official MCP registry.
    Populates _official_urls for is_official_mcp_url lookups.
    """
    global _official_urls

    if os.environ.get("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"):
        return

    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT_MS / 1000) as client:
            response = await client.get(
                "https://api.anthropic.com/mcp-registry/v0/servers?version=latest&visibility=commercial"
            )
            response.raise_for_status()
            data = response.json()

        urls = set()
        for entry in data.get("servers", []):
            for remote in entry.get("server", {}).get("remotes", []):
                normalized = _normalize_url(remote.get("url", ""))
                if normalized:
                    urls.add(normalized)

        _official_urls = urls
    except Exception:
        # Silently fail - is_official_mcp_url will return False
        pass


def is_official_mcp_url(normalized_url: str) -> bool:
    """
    Returns True iff the given (already-normalized via getLoggingSafeMcpBaseUrl)
    URL is in the official MCP registry. Undefined registry → False (fail-closed).

    Args:
        normalized_url: The normalized URL to check

    Returns:
        True if the URL is in the official registry, False otherwise
    """
    return _official_urls is not None and normalized_url in _official_urls


def reset_official_mcp_urls_for_testing() -> None:
    """Reset the official URLs cache for testing purposes."""
    global _official_urls
    _official_urls = None
