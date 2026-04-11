"""
Quota management for policy limits service.

Provides QuotaManager class for managing quota allocation and tracking.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from .types import PolicyCheckResult, QuotaLimit, QuotaStatus


class QuotaManager:
    """Manages quota allocation, tracking, and enforcement."""

    _quotas: Dict[str, QuotaLimit] = {}
    _allocation_history: Dict[str, list] = {}

    @classmethod
    def check_quota(
        cls,
        quota_name: str,
        user_id: Optional[str] = None,
    ) -> PolicyCheckResult:
        """Check if quota is available for use."""
        key = cls._make_key(quota_name, user_id)
        quota = cls._quotas.get(key)

        if not quota:
            return PolicyCheckResult(
                allowed=True,
                policy_name=quota_name,
                reason="No quota configured",
            )

        if quota.is_exceeded():
            return PolicyCheckResult(
                allowed=False,
                policy_name=quota_name,
                current_value=quota.used,
                max_value=quota.allocated,
                remaining=0,
                reset_at=quota.reset_at,
                reason=f"Quota exceeded: {quota.used}/{quota.allocated}",
            )

        return PolicyCheckResult(
            allowed=True,
            policy_name=quota_name,
            current_value=quota.used,
            max_value=quota.allocated,
            remaining=quota.available(),
        )

    @classmethod
    def allocate_quota(
        cls,
        quota_name: str,
        amount: float,
        user_id: Optional[str] = None,
        window_seconds: int = 86400,
    ) -> QuotaLimit:
        """Allocate quota to a user or organization."""
        key = cls._make_key(quota_name, user_id)
        quota = cls._quotas.get(key)

        if quota:
            quota.allocated += amount
            if quota.max_limit and quota.allocated > quota.max_limit:
                quota.allocated = quota.max_limit
        else:
            reset_at = datetime.utcnow() + timedelta(seconds=window_seconds)
            quota = QuotaLimit(
                quota_name=quota_name,
                allocated=amount,
                used=0,
                reserved=0,
                max_limit=amount,
                window_seconds=window_seconds,
                reset_at=reset_at,
            )
            cls._quotas[key] = quota

        if key not in cls._allocation_history:
            cls._allocation_history[key] = []
        cls._allocation_history[key].append({
            "amount": amount,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return quota

    @classmethod
    def release_quota(
        cls,
        quota_name: str,
        amount: float,
        user_id: Optional[str] = None,
    ) -> QuotaLimit:
        """Release quota back to the pool."""
        key = cls._make_key(quota_name, user_id)
        quota = cls._quotas.get(key)

        if not quota:
            raise ValueError(f"No quota found for {quota_name}")

        quota.used = max(0, quota.used - amount)
        return quota

    @classmethod
    def get_quota_usage(
        cls,
        quota_name: str,
        user_id: Optional[str] = None,
    ) -> Optional[QuotaStatus]:
        """Get current quota usage status."""
        key = cls._make_key(quota_name, user_id)
        quota = cls._quotas.get(key)

        if not quota:
            return None

        return QuotaStatus(
            quota_name=quota_name,
            allocated=quota.allocated,
            used=quota.used,
            reserved=quota.reserved,
            available=quota.available(),
            utilization_percent=quota.utilization_percent(),
            reset_at=quota.reset_at,
        )

    @classmethod
    def use_quota(
        cls,
        quota_name: str,
        amount: float,
        user_id: Optional[str] = None,
    ) -> PolicyCheckResult:
        """Use quota (consume resources)."""
        key = cls._make_key(quota_name, user_id)
        quota = cls._quotas.get(key)

        if not quota:
            return PolicyCheckResult(
                allowed=True,
                policy_name=quota_name,
                reason="No quota configured - unlimited",
            )

        if quota.available() < amount:
            return PolicyCheckResult(
                allowed=False,
                policy_name=quota_name,
                current_value=quota.used,
                max_value=quota.allocated,
                remaining=0,
                reset_at=quota.reset_at,
                reason=f"Insufficient quota: {quota.available()} available, {amount} requested",
            )

        quota.used += amount
        return PolicyCheckResult(
            allowed=True,
            policy_name=quota_name,
            current_value=quota.used,
            max_value=quota.allocated,
            remaining=quota.available(),
        )

    @classmethod
    def reserve_quota(
        cls,
        quota_name: str,
        amount: float,
        user_id: Optional[str] = None,
    ) -> bool:
        """Reserve quota for future use."""
        key = cls._make_key(quota_name, user_id)
        quota = cls._quotas.get(key)

        if not quota:
            return False

        if quota.available() < amount:
            return False

        quota.reserved += amount
        return True

    @classmethod
    def unreserve_quota(
        cls,
        quota_name: str,
        amount: float,
        user_id: Optional[str] = None,
    ) -> None:
        """Unreserve quota that was previously reserved."""
        key = cls._make_key(quota_name, user_id)
        quota = cls._quotas.get(key)

        if not quota:
            return

        quota.reserved = max(0, quota.reserved - amount)

    @classmethod
    def reset_quota(
        cls,
        quota_name: str,
        user_id: Optional[str] = None,
    ) -> None:
        """Reset quota usage to zero."""
        key = cls._make_key(quota_name, user_id)
        quota = cls._quotas.get(key)

        if quota:
            quota.used = 0
            quota.reserved = 0
            quota.reset_at = datetime.utcnow() + timedelta(seconds=quota.window_seconds)

    @classmethod
    def delete_quota(
        cls,
        quota_name: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Delete a quota configuration."""
        key = cls._make_key(quota_name, user_id)
        if key in cls._quotas:
            del cls._quotas[key]
            return True
        return False

    @classmethod
    def get_quota(
        cls,
        quota_name: str,
        user_id: Optional[str] = None,
    ) -> Optional[QuotaLimit]:
        """Get a specific quota."""
        key = cls._make_key(quota_name, user_id)
        return cls._quotas.get(key)

    @classmethod
    def get_all_quotas(
        cls,
        user_id: Optional[str] = None,
    ) -> Dict[str, QuotaLimit]:
        """Get all quotas for a user or organization-level quotas."""
        if user_id:
            key_prefix = f"{user_id}:"
            return {
                k: v for k, v in cls._quotas.items()
                if k.startswith(key_prefix)
            }
        return cls._quotas.copy()

    @classmethod
    def set_quota_limit(
        cls,
        quota_name: str,
        max_limit: float,
        user_id: Optional[str] = None,
        window_seconds: int = 86400,
    ) -> QuotaLimit:
        """Set the maximum limit for a quota."""
        key = cls._make_key(quota_name, user_id)
        quota = cls._quotas.get(key)

        if quota:
            quota.max_limit = max_limit
            if quota.allocated > max_limit:
                quota.allocated = max_limit
        else:
            reset_at = datetime.utcnow() + timedelta(seconds=window_seconds)
            quota = QuotaLimit(
                quota_name=quota_name,
                allocated=max_limit,
                used=0,
                reserved=0,
                max_limit=max_limit,
                window_seconds=window_seconds,
                reset_at=reset_at,
            )
            cls._quotas[key] = quota

        return quota

    @classmethod
    def get_allocation_history(
        cls,
        quota_name: str,
        user_id: Optional[str] = None,
    ) -> list:
        """Get allocation history for a quota."""
        key = cls._make_key(quota_name, user_id)
        return cls._allocation_history.get(key, [])

    @classmethod
    def _make_key(
        cls,
        quota_name: str,
        user_id: Optional[str] = None,
    ) -> str:
        """Create internal key for quota storage."""
        if user_id:
            return f"{user_id}:{quota_name}"
        return f"_global_:{quota_name}"

    @classmethod
    def reset_all_quotas(cls) -> None:
        """Reset all quotas."""
        cls._quotas.clear()
        cls._allocation_history.clear()
