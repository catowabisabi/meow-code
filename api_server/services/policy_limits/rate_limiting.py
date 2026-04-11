"""
Rate limiting for policy limits service.

Provides RateLimiter class for rate limiting operations.
"""

from datetime import datetime
from typing import Dict, Optional

from .limits import PolicyLimitManager
from .types import (
    DEFAULT_TIER_CONFIGS,
    PolicyCheckResult,
    RateLimitStatus,
    RateLimitTier,
    RateLimitTierConfig,
)


class RateLimiter:
    """Manages rate limiting for users based on their tier."""

    _request_counts: Dict[str, list] = {}
    _token_counts: Dict[str, list] = {}
    _tier_cache: Dict[str, RateLimitTier] = {}

    @classmethod
    def _cleanup_old_entries(cls, entries: list, window_seconds: int) -> list:
        now = datetime.utcnow().timestamp()
        cutoff = now - window_seconds
        return [e for e in entries if e > cutoff]

    @classmethod
    def get_rate_limit_tier(cls, user_id: str) -> RateLimitTier:
        """Get the rate limit tier for a user."""
        return cls._tier_cache.get(user_id, RateLimitTier.FREE)

    @classmethod
    def set_user_tier(cls, user_id: str, tier: RateLimitTier) -> None:
        """Set the rate limit tier for a user."""
        cls._tier_cache[user_id] = tier

    @classmethod
    def get_tier_config(cls, tier: RateLimitTier) -> RateLimitTierConfig:
        """Get the rate limit configuration for a tier."""
        return DEFAULT_TIER_CONFIGS.get(tier, DEFAULT_TIER_CONFIGS[RateLimitTier.FREE])

    @classmethod
    async def check_rate_limit(
        cls,
        user_id: str,
        tier: Optional[RateLimitTier] = None,
    ) -> PolicyCheckResult:
        """Check if the user is within their rate limit."""
        if tier is None:
            tier = cls.get_rate_limit_tier(user_id)

        config = cls.get_tier_config(tier)
        now = datetime.utcnow().timestamp()

        if user_id not in cls._request_counts:
            cls._request_counts[user_id] = []
        cls._request_counts[user_id] = cls._cleanup_old_entries(
            cls._request_counts[user_id], 60
        )

        request_count = len(cls._request_counts[user_id])
        max_requests = config.max_requests_per_minute

        if request_count >= max_requests:
            oldest_request = min(cls._request_counts[user_id]) if cls._request_counts[user_id] else now
            reset_at = datetime.fromtimestamp(oldest_request + 60)
            return PolicyCheckResult(
                allowed=False,
                policy_name="rate_limit",
                limit_type="requests_per_minute",
                current_value=float(request_count),
                max_value=float(max_requests),
                remaining=0,
                reset_at=reset_at,
                reason=f"Rate limit exceeded: {request_count}/{max_requests} requests per minute",
            )

        cls._request_counts[user_id].append(now)
        remaining = max_requests - request_count - 1
        reset_at = datetime.fromtimestamp(now + 60)

        return PolicyCheckResult(
            allowed=True,
            policy_name="rate_limit",
            limit_type="requests_per_minute",
            current_value=float(request_count + 1),
            max_value=float(max_requests),
            remaining=float(remaining),
            reset_at=reset_at,
        )

    @classmethod
    async def check_token_limit(
        cls,
        user_id: str,
        tokens: int,
        tier: Optional[RateLimitTier] = None,
    ) -> PolicyCheckResult:
        """Check if the user is within their token limit."""
        if tier is None:
            tier = cls.get_rate_limit_tier(user_id)

        config = cls.get_tier_config(tier)
        now = datetime.utcnow().timestamp()

        if user_id not in cls._token_counts:
            cls._token_counts[user_id] = []
        cls._token_counts[user_id] = cls._cleanup_old_entries(
            cls._token_counts[user_id], 3600
        )

        current_tokens = sum(cls._token_counts[user_id])
        max_tokens = config.max_tokens_per_hour

        if current_tokens + tokens > max_tokens:
            oldest_token_time = min(cls._token_counts[user_id]) if cls._token_counts[user_id] else now
            reset_at = datetime.fromtimestamp(oldest_token_time + 3600)
            return PolicyCheckResult(
                allowed=False,
                policy_name="token_limit",
                limit_type="tokens_per_hour",
                current_value=float(current_tokens),
                max_value=float(max_tokens),
                remaining=0,
                reset_at=reset_at,
                reason=f"Token limit exceeded: {current_tokens}/{max_tokens} tokens per hour",
            )

        cls._token_counts[user_id].append(tokens)
        remaining = max_tokens - current_tokens - tokens

        return PolicyCheckResult(
            allowed=True,
            policy_name="token_limit",
            limit_type="tokens_per_hour",
            current_value=float(current_tokens + tokens),
            max_value=float(max_tokens),
            remaining=float(remaining),
        )

    @classmethod
    def get_remaining_requests(
        cls,
        user_id: str,
        tier: Optional[RateLimitTier] = None,
    ) -> int:
        """Get remaining requests for user in current window."""
        if tier is None:
            tier = cls.get_rate_limit_tier(user_id)

        config = cls.get_tier_config(tier)

        if user_id not in cls._request_counts:
            return config.max_requests_per_minute

        cls._request_counts[user_id] = cls._cleanup_old_entries(
            cls._request_counts[user_id], 60
        )

        return max(0, config.max_requests_per_minute - len(cls._request_counts[user_id]))

    @classmethod
    def get_remaining_tokens(
        cls,
        user_id: str,
        tier: Optional[RateLimitTier] = None,
    ) -> int:
        """Get remaining tokens for user in current window."""
        if tier is None:
            tier = cls.get_rate_limit_tier(user_id)

        config = cls.get_tier_config(tier)

        if user_id not in cls._token_counts:
            return config.max_tokens_per_hour

        cls._token_counts[user_id] = cls._cleanup_old_entries(
            cls._token_counts[user_id], 3600
        )

        current_tokens = sum(cls._token_counts[user_id])
        return max(0, config.max_tokens_per_hour - current_tokens)

    @classmethod
    def apply_rate_limit(
        cls,
        user_id: str,
        tier: Optional[RateLimitTier] = None,
    ) -> bool:
        """Apply rate limit by recording a request. Returns True if allowed."""
        if tier is None:
            tier = cls.get_rate_limit_tier(user_id)

        config = cls.get_tier_config(tier)
        now = datetime.utcnow().timestamp()

        if user_id not in cls._request_counts:
            cls._request_counts[user_id] = []
        cls._request_counts[user_id] = cls._cleanup_old_entries(
            cls._request_counts[user_id], 60
        )

        if len(cls._request_counts[user_id]) >= config.max_requests_per_minute:
            return False

        cls._request_counts[user_id].append(now)
        return True

    @classmethod
    def get_rate_limit_headers(
        cls,
        user_id: str,
        tier: Optional[RateLimitTier] = None,
    ) -> Dict[str, str]:
        """Get rate limit headers for a response."""
        if tier is None:
            tier = cls.get_rate_limit_tier(user_id)

        config = cls.get_tier_config(tier)
        remaining_requests = cls.get_remaining_requests(user_id, tier)
        remaining_tokens = cls.get_remaining_tokens(user_id, tier)

        return {
            "X-RateLimit-Limit": str(config.max_requests_per_minute),
            "X-RateLimit-Remaining": str(remaining_requests),
            "X-RateLimit-Reset": str(int(datetime.utcnow().timestamp()) + 60),
            "X-RateLimit-Tier": tier.value,
            "X-TokenLimit-Limit": str(config.max_tokens_per_hour),
            "X-TokenLimit-Remaining": str(remaining_tokens),
            "X-TokenLimit-Reset": str(int(datetime.utcnow().timestamp()) + 3600),
        }

    @classmethod
    def get_rate_limit_status(
        cls,
        user_id: str,
        tier: Optional[RateLimitTier] = None,
    ) -> RateLimitStatus:
        """Get current rate limit status for a user."""
        if tier is None:
            tier = cls.get_rate_limit_tier(user_id)

        if user_id not in cls._request_counts:
            cls._request_counts[user_id] = []

        cls._request_counts[user_id] = cls._cleanup_old_entries(
            cls._request_counts[user_id], 60
        )

        if user_id not in cls._token_counts:
            cls._token_counts[user_id] = []

        cls._token_counts[user_id] = cls._cleanup_old_entries(
            cls._token_counts[user_id], 3600
        )

        return RateLimitStatus(
            user_id=user_id,
            requests_in_window=len(cls._request_counts[user_id]),
            tokens_in_window=sum(cls._token_counts[user_id]),
            window_reset_at=datetime.utcnow(),
            tier=tier,
            headers=cls.get_rate_limit_headers(user_id, tier),
        )

    @classmethod
    def reset_user_limits(cls, user_id: str) -> None:
        """Reset rate limits for a specific user."""
        if user_id in cls._request_counts:
            del cls._request_counts[user_id]
        if user_id in cls._token_counts:
            del cls._token_counts[user_id]
        if user_id in cls._tier_cache:
            del cls._tier_cache[user_id]

    @classmethod
    def reset_all_limits(cls) -> None:
        """Reset all rate limits."""
        cls._request_counts.clear()
        cls._token_counts.clear()
        PolicyLimitManager.reset_all_limits()
