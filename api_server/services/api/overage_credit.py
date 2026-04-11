"""
Overage credit grant service for managing credit grants.
"""

import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

import httpx


CACHE_TTL_MS = 60 * 60 * 1000


@dataclass
class OverageCreditGrantInfo:
    available: bool = False
    eligible: bool = False
    granted: bool = False
    amount_minor_units: Optional[int] = None
    currency: Optional[str] = None


@dataclass
class CachedGrantEntry:
    info: OverageCreditGrantInfo
    timestamp: float


def _get_oauth_config() -> Dict[str, str]:
    return {
        "BASE_API_URL": os.environ.get("CLAUDE_CODE_API_BASE_URL", "https://api.claude.ai"),
    }


def _get_auth_headers() -> Dict[str, Any]:
    return {"headers": {}, "error": None}


def _log_error(err: Exception) -> None:
    print(f"[overage_credit] Error: {err}", flush=True)


def _is_essential_traffic_only() -> bool:
    return os.environ.get("CLAUDE_CODE_ESSENTIAL_TRAFFIC_ONLY", "").lower() in ("true", "1", "yes")


def _get_global_config() -> Dict[str, Any]:
    return {}


def _save_global_config(updater) -> None:
    pass


def _get_oauth_account_info() -> Optional[Dict[str, Any]]:
    return None


async def _fetch_overage_credit_grant() -> Optional[OverageCreditGrantInfo]:
    try:
        headers = _get_auth_headers().get("headers", {})
        org_uuid = os.environ.get("CLAUDE_ORG_UUID", "")
        url = f"{_get_oauth_config()['BASE_API_URL']}/api/oauth/organizations/{org_uuid}/overage_credit_grant"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 200:
            return OverageCreditGrantInfo(**response.json())
        return None
    except Exception as err:
        _log_error(err)
        return None


def get_cached_overage_credit_grant() -> Optional[OverageCreditGrantInfo]:
    org_id = _get_oauth_account_info().get("organization_uuid") if _get_oauth_account_info() else None
    if not org_id:
        return None
    cached = _get_global_config().get("overageCreditGrantCache", {}).get(org_id)
    if not cached:
        return None
    if time.time() * 1000 - cached.get("timestamp", 0) > CACHE_TTL_MS:
        return None
    return cached.get("info")


def invalidate_overage_credit_grant_cache() -> None:
    org_id = _get_oauth_account_info().get("organization_uuid") if _get_oauth_account_info() else None
    if not org_id:
        return
    cache = _get_global_config().get("overageCreditGrantCache")
    if not cache or org_id not in cache:
        return

    def updater(current: Dict[str, Any]) -> Dict[str, Any]:
        next_cache = dict(current.get("overageCreditGrantCache", {}))
        if org_id in next_cache:
            del next_cache[org_id]
        return {**current, "overageCreditGrantCache": next_cache}

    _save_global_config(updater)


async def refresh_overage_credit_grant_cache() -> None:
    if _is_essential_traffic_only():
        return
    org_id = _get_oauth_account_info().get("organization_uuid") if _get_oauth_account_info() else None
    if not org_id:
        return
    info = await _fetch_overage_credit_grant()
    if not info:
        return

    def updater(current: Dict[str, Any]) -> Dict[str, Any]:
        prev_cached = current.get("overageCreditGrantCache", {}).get(org_id)
        existing = prev_cached.get("info") if prev_cached else None

        data_unchanged = (
            existing and
            existing.available == info.available and
            existing.eligible == info.eligible and
            existing.granted == info.granted and
            existing.amount_minor_units == info.amount_minor_units and
            existing.currency == info.currency
        )

        if data_unchanged and prev_cached:
            if time.time() * 1000 - prev_cached.get("timestamp", 0) <= CACHE_TTL_MS:
                return current

        entry: CachedGrantEntry = CachedGrantEntry(
            info=info if not data_unchanged else existing,
            timestamp=time.time() * 1000,
        )
        return {
            **current,
            "overageCreditGrantCache": {
                **(current.get("overageCreditGrantCache", {})),
                org_id: entry.__dict__,
            },
        }

    _save_global_config(updater)


def format_grant_amount(info: OverageCreditGrantInfo) -> Optional[str]:
    if info.amount_minor_units is None or not info.currency:
        return None
    if info.currency.upper() == "USD":
        dollars = info.amount_minor_units / 100
        if dollars == int(dollars):
            return f"${int(dollars)}"
        return f"${dollars:.2f}"
    return None
