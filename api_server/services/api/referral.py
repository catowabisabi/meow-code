"""
Referral service for managing guest passes and referral eligibility.
"""

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

import httpx


CACHE_EXPIRATION_MS = 24 * 60 * 60 * 1000


fetch_in_progress: Optional[Any] = None


@dataclass
class ReferralCampaign:
    CLAUDE_CODE_GUEST_PASS: str = "claude_code_guest_pass"


@dataclass
class ReferralEligibilityResponse:
    eligible: bool = False
    remaining_passes: Optional[int] = None
    referrer_reward: Optional[Dict[str, Any]] = None


@dataclass 
class ReferralRedemptionsResponse:
    redemptions: list = None


@dataclass
class ReferrerRewardInfo:
    currency: str = "USD"
    amount_minor_units: int = 0


def _get_oauth_config() -> Dict[str, str]:
    return {
        "BASE_API_URL": os.environ.get("CLAUDE_CODE_API_BASE_URL", "https://api.claude.ai"),
    }


def _get_auth_headers() -> Dict[str, Any]:
    return {"headers": {}, "error": None}


def _log_for_debugging(message: str) -> None:
    print(f"[referral] {message}", flush=True)


def _log_error(err: Exception) -> None:
    print(f"[referral] Error: {err}", flush=True)


def _is_essential_traffic_only() -> bool:
    return os.environ.get("CLAUDE_CODE_ESSENTIAL_TRAFFIC_ONLY", "").lower() in ("true", "1", "yes")


def _get_global_config() -> Dict[str, Any]:
    return {}


def _save_global_config(updater) -> None:
    pass


def _get_oauth_account_info() -> Optional[Dict[str, Any]]:
    return None


def _is_claude_ai_subscriber() -> bool:
    return True


def _get_subscription_type() -> str:
    return "max"


def should_check_for_passes() -> bool:
    return bool(
        _get_oauth_account_info() and
        _is_claude_ai_subscriber() and
        _get_subscription_type() == "max"
    )


async def fetch_referral_eligibility(
    campaign: str = "claude_code_guest_pass",
) -> ReferralEligibilityResponse:
    headers = {
        **_get_auth_headers().get("headers", {}),
        "x-organization-uuid": os.environ.get("CLAUDE_ORG_UUID", ""),
    }

    url = f"{_get_oauth_config()['BASE_API_URL']}/api/oauth/organizations/{os.environ.get('CLAUDE_ORG_UUID', '')}/referral/eligibility"

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            url,
            headers=headers,
            params={"campaign": campaign},
        )

    if response.status_code == 200:
        return ReferralEligibilityResponse(**response.json())
    return ReferralEligibilityResponse()


async def fetch_referral_redemptions(
    campaign: str = "claude_code_guest_pass",
) -> ReferralRedemptionsResponse:
    headers = {
        **_get_auth_headers().get("headers", {}),
        "x-organization-uuid": os.environ.get("CLAUDE_ORG_UUID", ""),
    }

    url = f"{_get_oauth_config()['BASE_API_URL']}/api/oauth/organizations/{os.environ.get('CLAUDE_ORG_UUID', '')}/referral/redemptions"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            url,
            headers=headers,
            params={"campaign": campaign},
        )

    if response.status_code == 200:
        return ReferralRedemptionsResponse(**response.json())
    return ReferralRedemptionsResponse()


def check_cached_passes_eligibility() -> Dict[str, Any]:
    if not should_check_for_passes():
        return {"eligible": False, "needsRefresh": False, "hasCache": False}

    org_id = _get_oauth_account_info().get("organization_uuid") if _get_oauth_account_info() else None
    if not org_id:
        return {"eligible": False, "needsRefresh": False, "hasCache": False}

    config = _get_global_config()
    cached_entry = config.get("passesEligibilityCache", {}).get(org_id)

    if not cached_entry:
        return {"eligible": False, "needsRefresh": True, "hasCache": False}

    eligible = cached_entry.get("eligible", False)
    timestamp = cached_entry.get("timestamp", 0)
    now = time.time() * 1000
    needs_refresh = now - timestamp > CACHE_EXPIRATION_MS

    return {
        "eligible": eligible,
        "needsRefresh": needs_refresh,
        "hasCache": True,
    }


CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "BRL": "R$",
    "CAD": "CA$",
    "AUD": "A$",
    "NZD": "NZ$",
    "SGD": "S$",
}


def format_credit_amount(reward: ReferrerRewardInfo) -> str:
    symbol = CURRENCY_SYMBOLS.get(reward.currency, f"{reward.currency} ")
    amount = reward.amount_minor_units / 100
    formatted = str(amount) if amount == int(amount) else f"{amount:.2f}"
    return f"{symbol}{formatted}"


def get_cached_referrer_reward() -> Optional[ReferrerRewardInfo]:
    org_id = _get_oauth_account_info().get("organization_uuid") if _get_oauth_account_info() else None
    if not org_id:
        return None
    config = _get_global_config()
    cached_entry = config.get("passesEligibilityCache", {}).get(org_id)
    if cached_entry and cached_entry.get("referrer_reward"):
        return ReferrerRewardInfo(**cached_entry["referrer_reward"])
    return None


def get_cached_remaining_passes() -> Optional[int]:
    org_id = _get_oauth_account_info().get("organization_uuid") if _get_oauth_account_info() else None
    if not org_id:
        return None
    config = _get_global_config()
    cached_entry = config.get("passesEligibilityCache", {}).get(org_id)
    return cached_entry.get("remaining_passes") if cached_entry else None


async def fetch_and_store_passes_eligibility() -> Optional[ReferralEligibilityResponse]:
    global fetch_in_progress

    if fetch_in_progress:
        _log_for_debugging("Passes: Reusing in-flight eligibility fetch")
        return await fetch_in_progress

    org_id = _get_oauth_account_info().get("organization_uuid") if _get_oauth_account_info() else None
    if not org_id:
        return None

    async def _do_fetch():
        try:
            response = await fetch_referral_eligibility()

            cache_entry = {
                **response.__dict__,
                "timestamp": time.time() * 1000,
            }

            def updater(current: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    **current,
                    "passesEligibilityCache": {
                        **(current.get("passesEligibilityCache", {})),
                        org_id: cache_entry,
                    },
                }

            _save_global_config(updater)

            _log_for_debugging(
                f"Passes eligibility cached for org {org_id}: {response.eligible}",
            )

            return response
        except Exception as error:
            _log_for_debugging("Failed to fetch and cache passes eligibility")
            _log_error(error)
            return None
        finally:
            nonlocal fetch_in_progress
            fetch_in_progress = None

    fetch_in_progress = _do_fetch()
    return await fetch_in_progress


async def get_cached_or_fetch_passes_eligibility() -> Optional[ReferralEligibilityResponse]:
    if not should_check_for_passes():
        return None

    org_id = _get_oauth_account_info().get("organization_uuid") if _get_oauth_account_info() else None
    if not org_id:
        return None

    config = _get_global_config()
    cached_entry = config.get("passesEligibilityCache", {}).get(org_id)
    now = time.time() * 1000

    if not cached_entry:
        _log_for_debugging(
            "Passes: No cache, fetching eligibility in background (command unavailable this session)",
        )
        asyncio.create_task(fetch_and_store_passes_eligibility())
        return None

    if now - cached_entry.get("timestamp", 0) > CACHE_EXPIRATION_MS:
        _log_for_debugging(
            "Passes: Cache stale, returning cached data and refreshing in background",
        )
        asyncio.create_task(fetch_and_store_passes_eligibility())
        return ReferralEligibilityResponse(
            eligible=cached_entry.get("eligible", False),
            remaining_passes=cached_entry.get("remaining_passes"),
            referrer_reward=cached_entry.get("referrer_reward"),
        )

    _log_for_debugging("Passes: Using fresh cached eligibility data")
    return ReferralEligibilityResponse(
        eligible=cached_entry.get("eligible", False),
        remaining_passes=cached_entry.get("remaining_passes"),
        referrer_reward=cached_entry.get("referrer_reward"),
    )


async def prefetch_passes_eligibility() -> None:
    if _is_essential_traffic_only():
        return

    asyncio.create_task(get_cached_or_fetch_passes_eligibility())
