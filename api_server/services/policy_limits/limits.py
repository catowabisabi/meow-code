"""
Limit management for policy limits service.

Provides PolicyLimitManager class for managing and checking limits.
"""

from datetime import datetime
from typing import Dict, List, Optional

from .types import (
    LimitConfig,
    PolicyCheckResult,
    PolicyLimit,
    RateLimitTier,
    UsageLimit,
)


class PolicyLimitManager:
    """Manages policy limits and checking if limits are reached."""

    _limits: Dict[str, PolicyLimit] = {}
    _usage_limits: Dict[str, UsageLimit] = {}
    _limit_configs: Dict[str, LimitConfig] = {}

    @classmethod
    def _cleanup_old_entries(cls, entries: List[float], window_seconds: int) -> List[float]:
        now = datetime.utcnow().timestamp()
        cutoff = now - window_seconds
        return [e for e in entries if e > cutoff]

    @classmethod
    def check_limit(
        cls,
        limit_type: str,
        value: float = 1.0,
    ) -> PolicyCheckResult:
        """Check if a limit has been reached."""
        limit = cls._limits.get(limit_type)
        if not limit:
            return PolicyCheckResult(
                allowed=True,
                policy_name=limit_type,
                reason="No limit configured",
            )

        now = datetime.utcnow().timestamp()
        if now >= limit.reset_at:
            limit.current_value = 0
            limit.reset_at = now + limit.window_seconds

        new_value = limit.current_value + value
        if new_value > limit.max_value:
            return PolicyCheckResult(
                allowed=False,
                policy_name=limit_type,
                limit_type=limit.limit_type,
                current_value=limit.current_value,
                max_value=limit.max_value,
                remaining=0,
                reset_at=datetime.fromtimestamp(limit.reset_at),
                reason=f"Limit exceeded: {limit.current_value}/{limit.max_value}",
            )

        return PolicyCheckResult(
            allowed=True,
            policy_name=limit_type,
            limit_type=limit.limit_type,
            current_value=new_value,
            max_value=limit.max_value,
            remaining=limit.max_value - new_value,
            reset_at=datetime.fromtimestamp(limit.reset_at),
        )

    @classmethod
    def get_current_usage(cls, limit_type: str) -> Optional[float]:
        """Get current usage for a limit."""
        limit = cls._limits.get(limit_type)
        if not limit:
            usage_limit = cls._usage_limits.get(limit_type)
            return usage_limit.current_usage if usage_limit else None
        return limit.current_value

    @classmethod
    def get_remaining_quota(cls, limit_type: str) -> Optional[float]:
        """Get remaining quota for a limit."""
        limit = cls._limits.get(limit_type)
        if not limit:
            usage_limit = cls._usage_limits.get(limit_type)
            return usage_limit.remaining() if usage_limit else None
        return max(0, limit.max_value - limit.current_value)

    @classmethod
    def reset_limit(cls, limit_type: str) -> None:
        """Reset a specific limit."""
        if limit_type in cls._limits:
            del cls._limits[limit_type]
        if limit_type in cls._usage_limits:
            del cls._usage_limits[limit_type]

    @classmethod
    def set_limit(
        cls,
        limit_type: str,
        max_value: float,
        window_seconds: int = 60,
        current_value: float = 0.0,
    ) -> PolicyLimit:
        """Set a limit with configuration."""
        now = datetime.utcnow().timestamp()
        limit = PolicyLimit(
            limit_type=limit_type,
            current_value=current_value,
            max_value=max_value,
            reset_at=now + window_seconds,
            window_seconds=window_seconds,
        )
        cls._limits[limit_type] = limit
        return limit

    @classmethod
    def get_limit(cls, limit_type: str) -> Optional[PolicyLimit]:
        """Get a specific limit."""
        return cls._limits.get(limit_type)

    @classmethod
    def get_all_limits(cls) -> Dict[str, PolicyLimit]:
        """Get all configured limits."""
        return cls._limits.copy()

    @classmethod
    def reset_all_limits(cls) -> None:
        """Reset all limits."""
        cls._limits.clear()
        cls._usage_limits.clear()

    @classmethod
    def configure_limit(cls, config: LimitConfig) -> None:
        """Configure a limit from a LimitConfig."""
        cls._limit_configs[config.limit_type] = config
        if config.enabled:
            cls.set_limit(
                limit_type=config.limit_type,
                max_value=config.max_value,
                window_seconds=config.window_seconds,
            )

    @classmethod
    def get_limit_config(cls, limit_type: str) -> Optional[LimitConfig]:
        """Get limit configuration."""
        return cls._limit_configs.get(limit_type)

    @classmethod
    def get_all_configs(cls) -> Dict[str, LimitConfig]:
        """Get all limit configurations."""
        return cls._limit_configs.copy()

    @classmethod
    def add_usage(cls, limit_type: str, value: float) -> float:
        """Add usage to a limit and return new value."""
        if limit_type not in cls._limits:
            return value
        limit = cls._limits[limit_type]
        limit.current_value += value
        return limit.current_value

    @classmethod
    def get_usage_for_tier(
        cls,
        tier: RateLimitTier,
        limit_type: str,
    ) -> Optional[UsageLimit]:
        """Get usage limit for a specific tier."""
        key = f"{tier.value}:{limit_type}"
        return cls._usage_limits.get(key)

    @classmethod
    def set_usage_limit(
        cls,
        tier: RateLimitTier,
        limit_type: str,
        max_usage: float,
        window_seconds: int = 3600,
    ) -> UsageLimit:
        """Set a usage limit for a tier."""
        key = f"{tier.value}:{limit_type}"
        usage_limit = UsageLimit(
            metric_name=limit_type,
            current_usage=0.0,
            max_usage=max_usage,
            window_seconds=window_seconds,
            reset_at=datetime.utcnow(),
        )
        cls._usage_limits[key] = usage_limit
        return usage_limit

    @classmethod
    def increment_usage(
        cls,
        tier: RateLimitTier,
        limit_type: str,
        value: float = 1.0,
    ) -> UsageLimit:
        """Increment usage for a tier's limit."""
        key = f"{tier.value}:{limit_type}"
        if key not in cls._usage_limits:
            cls.set_usage_limit(tier, limit_type, 100000)
        usage_limit = cls._usage_limits[key]
        usage_limit.current_usage += value
        return usage_limit

    @classmethod
    def check_usage_limit(
        cls,
        tier: RateLimitTier,
        limit_type: str,
    ) -> PolicyCheckResult:
        """Check if usage limit is exceeded for a tier."""
        key = f"{tier.value}:{limit_type}"
        usage_limit = cls._usage_limits.get(key)
        if not usage_limit:
            return PolicyCheckResult(
                allowed=True,
                policy_name=limit_type,
                reason="No usage limit configured",
            )

        if usage_limit.is_exceeded():
            return PolicyCheckResult(
                allowed=False,
                policy_name=limit_type,
                current_value=usage_limit.current_usage,
                max_value=usage_limit.max_usage,
                remaining=0,
                reason=f"Usage limit exceeded: {usage_limit.current_usage}/{usage_limit.max_usage}",
            )

        return PolicyCheckResult(
            allowed=True,
            policy_name=limit_type,
            current_value=usage_limit.current_usage,
            max_value=usage_limit.max_usage,
            remaining=usage_limit.remaining(),
        )
