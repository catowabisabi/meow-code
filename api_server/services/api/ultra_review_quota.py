"""
UltraReview quota service for checking review usage.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

import httpx


@dataclass
class UltrareviewQuotaResponse:
    reviews_used: int = 0
    reviews_limit: int = 0
    reviews_remaining: int = 0
    is_overage: bool = False


def _get_oauth_config() -> Dict[str, str]:
    return {
        "BASE_API_URL": os.environ.get("CLAUDE_CODE_API_BASE_URL", "https://api.claude.ai"),
    }


def _get_auth_headers() -> Dict[str, Any]:
    return {"headers": {}, "error": None}


def _log_for_debugging(message: str) -> None:
    print(f"[ultrareview] {message}", flush=True)


def _is_claude_ai_subscriber() -> bool:
    return True


async def fetch_ultrareview_quota() -> Optional[UltrareviewQuotaResponse]:
    if not _is_claude_ai_subscriber():
        return None
    try:
        headers = {
            **_get_auth_headers().get("headers", {}),
            "x-organization-uuid": os.environ.get("CLAUDE_ORG_UUID", ""),
        }
        url = f"{_get_oauth_config()['BASE_API_URL']}/v1/ultrareview/quota"

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 200:
            return UltrareviewQuotaResponse(**response.json())
        return None
    except Exception as error:
        _log_for_debugging(f"fetchUltrareviewQuota failed: {error}")
        return None
