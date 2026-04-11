"""OAuth type definitions for the OAuth 2.0 service."""

from dataclasses import dataclass, field
from typing import Literal, Optional

# Subscription type values
SubscriptionType = Literal["max", "pro", "enterprise", "team"]

# Rate limit tier - string representation
RateLimitTier = str

# Billing type - string representation
BillingType = str


@dataclass
class OAuthAccountInfo:
    """Account information from OAuth token response."""
    uuid: str
    email_address: str
    organization_uuid: Optional[str] = None


@dataclass
class OAuthOrganizationInfo:
    """Organization information from OAuth profile."""
    uuid: str
    organization_type: Optional[str] = None
    rate_limit_tier: Optional[str] = None
    has_extra_usage_enabled: Optional[bool] = None
    billing_type: Optional[str] = None
    subscription_created_at: Optional[str] = None


@dataclass
class OAuthAccountProfile:
    """Account profile information."""
    uuid: str
    email: str
    display_name: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class OAuthProfileResponse:
    """Full OAuth profile response from /api/oauth/profile endpoint."""
    account: Optional[OAuthAccountProfile] = None
    organization: Optional[OAuthOrganizationInfo] = None


@dataclass
class OAuthTokenExchangeResponse:
    """Response from token exchange endpoint."""
    access_token: str
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    account: Optional[OAuthAccountInfo] = None
    organization: Optional[OAuthOrganizationInfo] = None


@dataclass
class OAuthTokens:
    """Final OAuth tokens with profile information."""
    access_token: str
    refresh_token: Optional[str]
    expires_at: float  # Unix timestamp in milliseconds
    token_type: str = "Bearer"
    scope: Optional[str] = None
    scopes: list[str] = field(default_factory=list)
    subscription_type: SubscriptionType | None = None
    rate_limit_tier: RateLimitTier | None = None
    profile: Optional[OAuthProfileResponse] = None
    token_account: Optional[OAuthAccountInfo] = None


@dataclass
class UserRolesResponse:
    """Response from user roles endpoint."""
    organization_role: str
    workspace_role: str
    organization_name: str


@dataclass
class BillingTypeResponse:
    """Response containing billing type information."""
    billing_type: BillingType | None = None


@dataclass
class ReferralEligibilityResponse:
    """Response from referral eligibility endpoint."""
    eligible: bool
    current_period_end: Optional[str] = None
