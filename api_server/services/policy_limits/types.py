"""
Type definitions for policy limits service.

This module provides type definitions for:
- Policy limits (rate limits, usage limits, quota limits)
- Policy types and configurations
- Policy violations and check results
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PolicyType(str, Enum):
    """Types of policy restrictions."""

    RATE_LIMIT = "rate_limit"
    USAGE_LIMIT = "usage_limit"
    QUOTA_LIMIT = "quota_limit"
    FEATURE_ALLOW = "feature_allow"
    ESSENTIAL_TRAFFIC_ONLY = "essential_traffic_only"


class RateLimitTier(str, Enum):
    """Rate limiting tiers for different user levels."""

    FREE = "free"
    TEAM = "team"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


@dataclass
class PolicyLimit:
    """Represents a policy limit with its current state."""

    limit_type: str
    current_value: float
    max_value: float
    reset_at: float
    window_seconds: int = 60


@dataclass
class LimitConfig:
    """Configuration for a specific limit."""

    limit_type: str
    max_value: float
    window_seconds: int
    tier: RateLimitTier = RateLimitTier.FREE
    enabled: bool = True


class RateLimitTierConfig(BaseModel):
    """Rate limit configuration per tier."""

    tier: RateLimitTier
    max_requests_per_minute: int = 60
    max_tokens_per_hour: int = 100000
    max_concurrent_sessions: int = 5


class UsageLimit(BaseModel):
    """Usage limit for a specific metric."""

    metric_name: str
    current_usage: float = 0.0
    max_usage: float
    window_seconds: int = 3600
    reset_at: Optional[datetime] = None

    def is_exceeded(self) -> bool:
        """Check if the usage limit has been exceeded."""
        return self.current_usage >= self.max_usage

    def remaining(self) -> float:
        """Get remaining quota."""
        return max(0.0, self.max_usage - self.current_usage)


class QuotaLimit(BaseModel):
    """Quota limit configuration and state."""

    quota_name: str
    allocated: float
    used: float = 0.0
    reserved: float = 0.0
    max_limit: Optional[float] = None
    window_seconds: int = 86400  # Daily by default
    reset_at: Optional[datetime] = None

    def available(self) -> float:
        """Get available quota (allocated - used - reserved)."""
        return max(0.0, self.allocated - self.used - self.reserved)

    def is_exceeded(self) -> bool:
        """Check if quota is exhausted."""
        return self.available() <= 0

    def utilization_percent(self) -> float:
        """Get utilization percentage."""
        if self.allocated <= 0:
            return 0.0
        return (self.used / self.allocated) * 100


class PolicyViolation(BaseModel):
    """Represents a policy violation."""

    violation_type: str
    policy_name: str
    message: str
    severity: str = "error"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "violation_type": self.violation_type,
            "policy_name": self.policy_name,
            "message": self.message,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "org_id": self.org_id,
            "details": self.details,
        }


class PolicyCheckResult(BaseModel):
    """Result of a policy check."""

    allowed: bool
    policy_name: str
    reason: Optional[str] = None
    limit_type: Optional[str] = None
    current_value: Optional[float] = None
    max_value: Optional[float] = None
    remaining: Optional[float] = None
    reset_at: Optional[datetime] = None
    violation: Optional[PolicyViolation] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "allowed": self.allowed,
            "policy_name": self.policy_name,
            "reason": self.reason,
        }
        if self.limit_type:
            result["limit_type"] = self.limit_type
        if self.current_value is not None:
            result["current_value"] = self.current_value
        if self.max_value is not None:
            result["max_value"] = self.max_value
        if self.remaining is not None:
            result["remaining"] = self.remaining
        if self.reset_at:
            result["reset_at"] = self.reset_at.isoformat()
        if self.violation:
            result["violation"] = self.violation.to_dict()
        return result


class PolicyRestrictions(BaseModel):
    """Container for policy restrictions from API."""

    restrictions: Dict[str, Dict[str, bool]] = Field(default_factory=dict)

    def is_allowed(self, policy_name: str) -> bool:
        """Check if a policy is allowed."""
        restriction = self.restrictions.get(policy_name)
        if restriction is None:
            return True  # Unknown policy = allowed
        return restriction.get("allowed", True)

    def get_restriction(self, policy_name: str) -> Optional[Dict[str, bool]]:
        """Get restriction for a policy."""
        return self.restrictions.get(policy_name)


class RateLimitStatus(BaseModel):
    """Current rate limit status for a user."""

    user_id: str
    requests_in_window: int = 0
    tokens_in_window: int = 0
    window_reset_at: datetime
    tier: RateLimitTier = RateLimitTier.FREE
    headers: Dict[str, str] = Field(default_factory=dict)

    def requests_remaining(self, max_requests: int) -> int:
        """Get remaining requests in current window."""
        return max(0, max_requests - self.requests_in_window)

    def tokens_remaining(self, max_tokens: int) -> int:
        """Get remaining tokens in current window."""
        return max(0, max_tokens - self.tokens_in_window)


class QuotaStatus(BaseModel):
    """Current quota status for a user/organization."""

    quota_name: str
    allocated: float
    used: float
    reserved: float
    available: float
    utilization_percent: float
    reset_at: Optional[datetime] = None


class ViolationHistoryEntry(BaseModel):
    """Entry in violation history."""

    violation: PolicyViolation
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class PolicyConfig(BaseModel):
    """Policy configuration for an organization."""

    org_id: str
    policy_type: PolicyType
    enabled: bool = True
    limits: List[LimitConfig] = Field(default_factory=list)
    restrictions: Dict[str, bool] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None

    def get_limit(self, limit_type: str) -> Optional[LimitConfig]:
        """Get a specific limit config."""
        for limit in self.limits:
            if limit.limit_type == limit_type:
                return limit
        return None


# Default tier configurations
DEFAULT_TIER_CONFIGS: Dict[RateLimitTier, RateLimitTierConfig] = {
    RateLimitTier.FREE: RateLimitTierConfig(
        tier=RateLimitTier.FREE,
        max_requests_per_minute=60,
        max_tokens_per_hour=100000,
        max_concurrent_sessions=5,
    ),
    RateLimitTier.TEAM: RateLimitTierConfig(
        tier=RateLimitTier.TEAM,
        max_requests_per_minute=300,
        max_tokens_per_hour=500000,
        max_concurrent_sessions=20,
    ),
    RateLimitTier.ENTERPRISE: RateLimitTierConfig(
        tier=RateLimitTier.ENTERPRISE,
        max_requests_per_minute=1000,
        max_tokens_per_hour=2000000,
        max_concurrent_sessions=100,
    ),
    RateLimitTier.UNLIMITED: RateLimitTierConfig(
        tier=RateLimitTier.UNLIMITED,
        max_requests_per_minute=10000,
        max_tokens_per_hour=10000000,
        max_concurrent_sessions=500,
    ),
}


# Policies that default to denied when essential-traffic-only mode is active
ESSENTIAL_TRAFFIC_DENY_ON_MISS: set = {"allow_product_feedback"}
