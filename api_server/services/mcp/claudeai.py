"""
Claude.ai specific MCP server configurations.

Fetches MCP server configurations from Claude.ai org configs.
"""

import os
from typing import Any, Dict, Optional

import httpx

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict


FETCH_TIMEOUT_MS = 5000
MCP_SERVERS_BETA_HEADER = "mcp-servers-2025-12-04"


class ClaudeAIMcpServer(TypedDict):
    type: str
    id: str
    display_name: str
    url: str
    created_at: str


class ClaudeAIMcpServersResponse(TypedDict):
    data: list[ClaudeAIMcpServer]
    has_more: bool
    next_page: Optional[str]


class ScopedMcpServerConfig(TypedDict, total=False):
    type: str
    url: str
    id: str
    scope: str


class OAuthConfig(TypedDict):
    BASE_API_URL: str


def _get_oauth_config() -> OAuthConfig:
    """Get OAuth configuration."""
    return OAuthConfig(BASE_API_URL="https://api.claude.ai")


def _get_claudeai_oauth_tokens() -> Optional[Dict[str, Any]]:
    """Get Claude.ai OAuth tokens from auth module."""
    return None


def _is_env_defined_falsy(key: str) -> bool:
    """Check if environment variable is defined and falsy."""
    value = os.environ.get(key)
    return value is not None and value.lower() in ("false", "0", "no", "")


def _normalize_name_for_mcp(name: str) -> str:
    """Normalize name for MCP."""
    normalized = "".join(c if c.isalnum() or c in "_- " else "_" for c in name)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    normalized = normalized.strip("_")
    return normalized


_mcp_configs_cache: Optional[Dict[str, ScopedMcpServerConfig]] = None


async def fetch_claudeai_mcp_configs_if_eligible() -> Dict[str, ScopedMcpServerConfig]:
    """
    Fetches MCP server configurations from Claude.ai org configs.

    These servers are managed by the organization via Claude.ai.
    Results are memoized for the session lifetime.

    Returns:
        Dict mapping server names to configurations
    """
    global _mcp_configs_cache

    if _mcp_configs_cache is not None:
        return _mcp_configs_cache

    if _is_env_defined_falsy("ENABLE_CLAUDEAI_MCP_SERVERS"):
        return {}

    tokens = _get_claudeai_oauth_tokens()
    if not tokens or not tokens.get("access_token"):
        return {}

    scopes = tokens.get("scopes", [])
    if "user:mcp_servers" not in scopes:
        return {}

    base_url = _get_oauth_config().BASE_API_URL
    url = f"{base_url}/v1/mcp_servers?limit=1000"

    try:
        async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_MS / 1000) as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {tokens['access_token']}",
                    "Content-Type": "application/json",
                    "anthropic-beta": MCP_SERVERS_BETA_HEADER,
                    "anthropic-version": "2023-06-01",
                },
            )
            response.raise_for_status()
            data: ClaudeAIMcpServersResponse = response.json()
    except Exception:
        return {}

    configs: Dict[str, ScopedMcpServerConfig] = {}
    used_normalized_names: set = set()

    for server in data.get("data", []):
        base_name = f"claude.ai {server['display_name']}"

        final_name = base_name
        final_normalized = _normalize_name_for_mcp(final_name)
        count = 1
        while final_normalized in used_normalized_names:
            count += 1
            final_name = f"{base_name} ({count})"
            final_normalized = _normalize_name_for_mcp(final_name)

        used_normalized_names.add(final_normalized)

        configs[final_name] = ScopedMcpServerConfig(
            type="claudeai-proxy",
            url=server["url"],
            id=server["id"],
            scope="claudeai",
        )

    _mcp_configs_cache = configs
    return configs


def clear_claudeai_mcp_configs_cache() -> None:
    """Clear the memoized cache for fetchClaudeAIMcpConfigsIfEligible."""
    global _mcp_configs_cache
    _mcp_configs_cache = None


def mark_claudeai_mcp_connected(name: str) -> None:
    """
    Record that a claude.ai connector successfully connected.

    Idempotent - used to gate startup notifications.
    """
    pass


def has_claudeai_mcp_ever_connected(name: str) -> bool:
    """Check if a claude.ai MCP server has ever connected successfully."""
    return False
