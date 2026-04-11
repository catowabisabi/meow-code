"""OAuth 2.0 service for api_server.

This module provides OAuth 2.0 authorization code flow with PKCE support,
following the TypeScript implementation in _claude_code_leaked_source_code/src/services/oauth/.
"""

from .types import (
    BillingType,
    OAuthAccountInfo,
    OAuthAccountProfile,
    OAuthOrganizationInfo,
    OAuthProfileResponse,
    OAuthTokenExchangeResponse,
    OAuthTokens,
    RateLimitTier,
    ReferralEligibilityResponse,
    SubscriptionType,
    UserRolesResponse,
)

from .config import (
    ALL_OAUTH_SCOPES,
    CLAUDE_AI_INFERENCE_SCOPE,
    CLAUDE_AI_OAUTH_SCOPES,
    CLAUDE_AI_ORIGIN,
    CLAUDE_AI_PROFILE_SCOPE,
    CONSOLE_OAUTH_SCOPES,
    CONSOLE_SCOPE,
    MCP_CLIENT_METADATA_URL,
    OAUTH_BETA_HEADER,
    OauthConfig,
    get_oauth_config,
)

from .crypto import (
    generate_code_challenge,
    generate_code_verifier,
    generate_state,
)

from .client import (
    build_auth_url,
    exchange_code_for_tokens,
    fetch_and_store_user_roles,
    fetch_profile_info,
    is_oauth_token_expired,
    parse_scopes,
    refresh_oauth_token,
    should_use_claude_ai_auth,
)

from .auth_code_listener import AuthCodeListener

from .oauth_service import OAuthService

from .oauth_profile import get_oauth_profile_from_oauth_token


__all__ = [
    # Types
    "BillingType",
    "OAuthAccountInfo",
    "OAuthAccountProfile",
    "OAuthOrganizationInfo",
    "OAuthProfileResponse",
    "OAuthTokenExchangeResponse",
    "OAuthTokens",
    "RateLimitTier",
    "ReferralEligibilityResponse",
    "SubscriptionType",
    "UserRolesResponse",
    # Config
    "ALL_OAUTH_SCOPES",
    "CLAUDE_AI_INFERENCE_SCOPE",
    "CLAUDE_AI_OAUTH_SCOPES",
    "CLAUDE_AI_ORIGIN",
    "CLAUDE_AI_PROFILE_SCOPE",
    "CONSOLE_OAUTH_SCOPES",
    "CONSOLE_SCOPE",
    "MCP_CLIENT_METADATA_URL",
    "OAUTH_BETA_HEADER",
    "OauthConfig",
    "get_oauth_config",
    # Crypto
    "generate_code_challenge",
    "generate_code_verifier",
    "generate_state",
    # Client
    "build_auth_url",
    "exchange_code_for_tokens",
    "fetch_and_store_user_roles",
    "fetch_profile_info",
    "is_oauth_token_expired",
    "parse_scopes",
    "refresh_oauth_token",
    "should_use_claude_ai_auth",
    # Auth Code Listener
    "AuthCodeListener",
    # OAuth Service
    "OAuthService",
    # Profile
    "get_oauth_profile_from_oauth_token",
]
