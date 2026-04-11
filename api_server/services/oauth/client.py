"""OAuth client functions for handling authentication flows with Claude services."""

import httpx
from typing import Optional

from .config import (
    ALL_OAUTH_SCOPES,
    CLAUDE_AI_INFERENCE_SCOPE,
    CLAUDE_AI_OAUTH_SCOPES,
    get_oauth_config,
)
from .types import (
    OAuthAccountInfo,
    OAuthTokenExchangeResponse,
    OAuthTokens,
    SubscriptionType,
)


def should_use_claude_ai_auth(scopes: Optional[list[str]]) -> bool:
    """Check if the user has Claude.ai authentication scope."""
    return bool(scopes and CLAUDE_AI_INFERENCE_SCOPE in scopes)


def parse_scopes(scope_string: Optional[str]) -> list[str]:
    """Parse scope string into list of scopes."""
    if not scope_string:
        return []
    return [s for s in scope_string.split(" ") if s]


def build_auth_url(
    code_challenge: str,
    state: str,
    port: int,
    is_manual: bool,
    login_with_claude_ai: Optional[bool] = None,
    inference_only: Optional[bool] = None,
    org_uuid: Optional[str] = None,
    login_hint: Optional[str] = None,
    login_method: Optional[str] = None,
) -> str:
    """
    Build OAuth authorization URL.
    
    Args:
        code_challenge: PKCE code challenge
        state: State parameter for CSRF protection
        port: Port for localhost callback
        is_manual: Whether using manual redirect URL
        login_with_claude_ai: Whether to use Claude.ai authorization
        inference_only: Whether to request only inference scope
        org_uuid: Organization UUID to pre-select
        login_hint: Email to pre-populate on login form
        login_method: Specific login method (e.g. 'sso', 'magic_link', 'google')
    """
    config = get_oauth_config()
    auth_url_base = (
        config.claude_ai_authorize_url
        if login_with_claude_ai
        else config.console_authorize_url
    )

    auth_url = f"{auth_url_base}?code=true"
    auth_url += f"&client_id={config.client_id}"
    auth_url += "&response_type=code"
    
    redirect_uri = (
        config.manual_redirect_url if is_manual else f"http://localhost:{port}/callback"
    )
    auth_url += f"&redirect_uri={redirect_uri}"
    
    scopes_to_use = [CLAUDE_AI_INFERENCE_SCOPE] if inference_only else ALL_OAUTH_SCOPES
    auth_url += f"&scope={' '.join(scopes_to_use)}"
    auth_url += f"&code_challenge={code_challenge}"
    auth_url += "&code_challenge_method=S256"
    auth_url += f"&state={state}"
    
    if org_uuid:
        auth_url += f"&orgUUID={org_uuid}"
    
    if login_hint:
        auth_url += f"&login_hint={login_hint}"
    
    if login_method:
        auth_url += f"&login_method={login_method}"
    
    return auth_url


async def exchange_code_for_tokens(
    authorization_code: str,
    state: str,
    code_verifier: str,
    port: int,
    use_manual_redirect: bool = False,
    expires_in: Optional[int] = None,
) -> OAuthTokenExchangeResponse:
    """
    Exchange authorization code for tokens.
    
    Args:
        authorization_code: The authorization code from OAuth callback
        state: State parameter for verification
        code_verifier: PKCE code verifier
        port: Port for localhost callback
        use_manual_redirect: Whether to use manual redirect URL
        expires_in: Token expiration time in seconds
    
    Returns:
        OAuthTokenExchangeResponse with access and refresh tokens
    """
    config = get_oauth_config()
    
    redirect_uri = (
        config.manual_redirect_url if use_manual_redirect else f"http://localhost:{port}/callback"
    )
    
    request_body = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": redirect_uri,
        "client_id": config.client_id,
        "code_verifier": code_verifier,
        "state": state,
    }
    
    if expires_in is not None:
        request_body["expires_in"] = expires_in
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            config.token_url,
            json=request_body,
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
    
    if response.status_code != 200:
        if response.status_code == 401:
            raise Exception("Authentication failed: Invalid authorization code")
        raise Exception(f"Token exchange failed ({response.status_code}): {response.text}")
    
    data = response.json()
    
    return OAuthTokenExchangeResponse(
        access_token=data["access_token"],
        expires_in=data["expires_in"],
        refresh_token=data.get("refresh_token"),
        scope=data.get("scope"),
        account=OAuthAccountInfo(
            uuid=data.get("account", {}).get("uuid", ""),
            email_address=data.get("account", {}).get("email_address", ""),
            organization_uuid=data.get("organization", {}).get("uuid"),
        ) if data.get("account") else None,
        organization=None,
    )


async def refresh_oauth_token(
    refresh_token: str,
    scopes: Optional[list[str]] = None,
) -> OAuthTokens:
    """
    Refresh OAuth token using refresh token.
    
    Args:
        refresh_token: The refresh token
        scopes: Optional specific scopes to request
        
    Returns:
        OAuthTokens with new access token and optionally new refresh token
    """
    config = get_oauth_config()
    
    requested_scopes = scopes if scopes else CLAUDE_AI_OAUTH_SCOPES
    
    request_body = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": config.client_id,
        "scope": " ".join(requested_scopes),
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            config.token_url,
            json=request_body,
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
    
    if response.status_code != 200:
        raise Exception(f"Token refresh failed: {response.text}")
    
    data = response.json()
    
    access_token = data["access_token"]
    new_refresh_token = data.get("refresh_token", refresh_token)
    expires_in = data["expires_in"]
    
    expires_at = _get_current_time_ms() + expires_in * 1000
    parsed_scopes = parse_scopes(data.get("scope"))
    
    profile_info = await fetch_profile_info(access_token)
    
    result_scopes = parsed_scopes
    subscription_type = profile_info["subscription_type"]
    rate_limit_tier = profile_info["rate_limit_tier"]
    raw_profile = profile_info["raw_profile"]
    
    token_account = None
    if data.get("account"):
        token_account = OAuthAccountInfo(
            uuid=data["account"]["uuid"],
            email_address=data["account"]["email_address"],
            organization_uuid=data.get("organization", {}).get("uuid"),
        )
    
    return OAuthTokens(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_at=expires_at,
        token_type="Bearer",
        scopes=result_scopes,
        subscription_type=subscription_type,
        rate_limit_tier=rate_limit_tier,
        profile=raw_profile,
        token_account=token_account,
    )


async def fetch_profile_info(access_token: str) -> dict:
    """
    Fetch profile info from OAuth token.
    
    Args:
        access_token: The OAuth access token
        
    Returns:
        Dictionary with subscription_type, rate_limit_tier, and other profile data
    """
    from .oauth_profile import get_oauth_profile_from_oauth_token
    
    profile = await get_oauth_profile_from_oauth_token(access_token)
    org_type = profile.organization.organization_type if profile.organization else None
    
    subscription_type: SubscriptionType | None = None
    if org_type == "claude_max":
        subscription_type = "max"
    elif org_type == "claude_pro":
        subscription_type = "pro"
    elif org_type == "claude_enterprise":
        subscription_type = "enterprise"
    elif org_type == "claude_team":
        subscription_type = "team"
    
    result = {
        "subscription_type": subscription_type,
        "rate_limit_tier": profile.organization.rate_limit_tier if profile.organization else None,
        "has_extra_usage_enabled": (
            profile.organization.has_extra_usage_enabled
            if profile.organization else None
        ),
        "billing_type": (
            profile.organization.billing_type
            if profile.organization else None
        ),
        "raw_profile": profile,
    }
    
    if profile.account and profile.account.display_name:
        result["display_name"] = profile.account.display_name
    
    if profile.account and profile.account.created_at:
        result["account_created_at"] = profile.account.created_at
    
    if profile.organization and profile.organization.subscription_created_at:
        result["subscription_created_at"] = profile.organization.subscription_created_at
    
    return result


def is_oauth_token_expired(expires_at: Optional[float]) -> bool:
    """
    Check if OAuth token is expired or about to expire.
    
    Uses a 5-minute buffer before expiration.
    """
    if expires_at is None:
        return False
    
    buffer_time = 5 * 60 * 1000
    now = _get_current_time_ms()
    expires_with_buffer = now + buffer_time
    return expires_with_buffer >= expires_at


async def fetch_and_store_user_roles(access_token: str) -> None:
    """Fetch user roles and store them in config."""
    config = get_oauth_config()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            config.roles_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15.0,
        )
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch user roles: {response.text}")


def _get_current_time_ms() -> float:
    """Get current time in milliseconds."""
    import time
    return time.time() * 1000
