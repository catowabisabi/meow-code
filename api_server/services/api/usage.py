from dataclasses import dataclass
from typing import Optional, Dict, Any
import httpx


@dataclass
class RateLimit:
    utilization: Optional[float]
    resets_at: Optional[str]


@dataclass
class ExtraUsage:
    is_enabled: bool
    monthly_limit: Optional[float]
    used_credits: Optional[float]
    utilization: Optional[float]


@dataclass
class Utilization:
    five_hour: Optional[RateLimit] = None
    seven_day: Optional[RateLimit] = None
    seven_day_oauth_apps: Optional[RateLimit] = None
    seven_day_opus: Optional[RateLimit] = None
    seven_day_sonnet: Optional[RateLimit] = None
    extra_usage: Optional[ExtraUsage] = None


def _get_oauth_config() -> Dict[str, str]:
    return {
        "BASE_API_URL": "https://api.claude.ai",
    }


def _get_auth_headers() -> Dict[str, Any]:
    return {"headers": {}}


async def fetch_utilization() -> Optional[Utilization]:
    # Placeholder implementation - actual implementation would use
    # OAuth token and profile scope checks from the auth module
    base_url = _get_oauth_config()["BASE_API_URL"]
    
    auth_result = _get_auth_headers()
    if "error" in auth_result:
        return None
    
    headers = {
        "Content-Type": "application/json",
        **auth_result.get("headers", {}),
    }
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{base_url}/api/oauth/usage",
                headers=headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                return _parse_utilization(data)
            return None
    except Exception:
        return None


def _parse_utilization(data: Dict[str, Any]) -> Utilization:
    five_hour = _parse_rate_limit(data.get("five_hour"))
    seven_day = _parse_rate_limit(data.get("seven_day"))
    seven_day_oauth_apps = _parse_rate_limit(data.get("seven_day_oauth_apps"))
    seven_day_opus = _parse_rate_limit(data.get("seven_day_opus"))
    seven_day_sonnet = _parse_rate_limit(data.get("seven_day_sonnet"))
    extra_usage = _parse_extra_usage(data.get("extra_usage"))
    
    return Utilization(
        five_hour=five_hour,
        seven_day=seven_day,
        seven_day_oauth_apps=seven_day_oauth_apps,
        seven_day_opus=seven_day_opus,
        seven_day_sonnet=seven_day_sonnet,
        extra_usage=extra_usage,
    )


def _parse_rate_limit(data: Optional[Dict[str, Any]]) -> Optional[RateLimit]:
    if data is None:
        return None
    return RateLimit(
        utilization=data.get("utilization"),
        resets_at=data.get("resets_at"),
    )


def _parse_extra_usage(data: Optional[Dict[str, Any]]) -> Optional[ExtraUsage]:
    if data is None:
        return None
    return ExtraUsage(
        is_enabled=data.get("is_enabled", False),
        monthly_limit=data.get("monthly_limit"),
        used_credits=data.get("used_credits"),
        utilization=data.get("utilization"),
    )
