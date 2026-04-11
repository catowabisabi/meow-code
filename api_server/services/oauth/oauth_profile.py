"""Functions for fetching OAuth profile information."""

import httpx

from .config import get_oauth_config
from .types import OAuthProfileResponse


async def get_oauth_profile_from_oauth_token(
    access_token: str,
) -> OAuthProfileResponse | None:
    """
    Fetch OAuth profile using access token.
    
    Args:
        access_token: The OAuth access token
        
    Returns:
        OAuthProfileResponse or None if fetch fails
    """
    config = get_oauth_config()
    endpoint = f"{config.base_api_url}/api/oauth/profile"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        account = None
        if data.get("account"):
            account_data = data["account"]
            from .types import OAuthAccountProfile
            account = OAuthAccountProfile(
                uuid=account_data.get("uuid", ""),
                email=account_data.get("email", ""),
                display_name=account_data.get("display_name"),
                created_at=account_data.get("created_at"),
            )
        
        organization = None
        if data.get("organization"):
            org_data = data["organization"]
            from .types import OAuthOrganizationInfo
            organization = OAuthOrganizationInfo(
                uuid=org_data.get("uuid", ""),
                organization_type=org_data.get("organization_type"),
                rate_limit_tier=org_data.get("rate_limit_tier"),
                has_extra_usage_enabled=org_data.get("has_extra_usage_enabled"),
                billing_type=org_data.get("billing_type"),
                subscription_created_at=org_data.get("subscription_created_at"),
            )
        
        return OAuthProfileResponse(
            account=account,
            organization=organization,
        )
    except Exception:
        return None
