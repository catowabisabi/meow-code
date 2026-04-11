"""
Policy configuration for policy limits service.

Provides functions for loading and managing policy configurations.
"""

from datetime import datetime
from typing import Dict, Optional

from .limits import PolicyLimitManager
from .types import (
    ESSENTIAL_TRAFFIC_DENY_ON_MISS,
    DEFAULT_TIER_CONFIGS,
    PolicyConfig,
    PolicyRestrictions,
    PolicyType,
    RateLimitTier,
    RateLimitTierConfig,
)


_policy_cache: Dict[str, PolicyRestrictions] = {}
_org_policies: Dict[str, PolicyConfig] = {}
_is_essential_traffic_only: bool = False


def load_policy_config(
    org_id: str,
    restrictions: Dict[str, Dict[str, bool]],
) -> PolicyConfig:
    """Load policy configuration for an organization."""
    policy = PolicyConfig(
        org_id=org_id,
        policy_type=PolicyType.RATE_LIMIT,
        enabled=True,
        restrictions={k: v.get("allowed", True) for k, v in restrictions.items()},
    )
    _org_policies[org_id] = policy
    _policy_cache[org_id] = PolicyRestrictions(restrictions=restrictions)
    return policy


def get_policy_for_org(org_id: str) -> Optional[PolicyConfig]:
    """Get policy configuration for an organization."""
    return _org_policies.get(org_id)


def get_restrictions_for_org(org_id: str) -> Optional[PolicyRestrictions]:
    """Get policy restrictions for an organization."""
    return _policy_cache.get(org_id)


def update_policy(
    org_id: str,
    policy_name: str,
    allowed: bool,
) -> PolicyConfig:
    """Update a specific policy for an organization."""
    if org_id not in _org_policies:
        _org_policies[org_id] = PolicyConfig(
            org_id=org_id,
            policy_type=PolicyType.RATE_LIMIT,
        )

    policy = _org_policies[org_id]
    policy.restrictions[policy_name] = allowed
    policy.updated_at = datetime.utcnow()

    if org_id in _policy_cache:
        _policy_cache[org_id].restrictions[policy_name] = {"allowed": allowed}

    return policy


def is_policy_allowed(policy_name: str, org_id: Optional[str] = None) -> bool:
    """Check if a policy is allowed for an organization."""
    if org_id and org_id in _policy_cache:
        restrictions = _policy_cache[org_id]
        return restrictions.is_allowed(policy_name)

    if _is_essential_traffic_only and policy_name in ESSENTIAL_TRAFFIC_DENY_ON_MISS:
        return False

    return True


def set_essential_traffic_only(enabled: bool) -> None:
    """Set essential traffic only mode."""
    global _is_essential_traffic_only
    _is_essential_traffic_only = enabled


def is_essential_traffic_only() -> bool:
    """Check if essential traffic only mode is enabled."""
    return _is_essential_traffic_only


def get_all_policies() -> Dict[str, PolicyConfig]:
    """Get all organization policies."""
    return _org_policies.copy()


def delete_org_policy(org_id: str) -> bool:
    """Delete policy configuration for an organization."""
    if org_id in _org_policies:
        del _org_policies[org_id]
    if org_id in _policy_cache:
        del _policy_cache[org_id]
        return True
    return False


def configure_tier_limits(tier: RateLimitTier, config: RateLimitTierConfig) -> None:
    """Configure rate limits for a specific tier."""
    DEFAULT_TIER_CONFIGS[tier] = config

    PolicyLimitManager.set_usage_limit(
        tier=tier,
        limit_type="requests_per_minute",
        max_usage=float(config.max_requests_per_minute),
        window_seconds=60,
    )
    PolicyLimitManager.set_usage_limit(
        tier=tier,
        limit_type="tokens_per_hour",
        max_usage=float(config.max_tokens_per_hour),
        window_seconds=3600,
    )
    PolicyLimitManager.set_usage_limit(
        tier=tier,
        limit_type="concurrent_sessions",
        max_usage=float(config.max_concurrent_sessions),
        window_seconds=86400,
    )


def get_tier_config(tier: RateLimitTier) -> RateLimitTierConfig:
    """Get rate limit configuration for a tier."""
    return DEFAULT_TIER_CONFIGS.get(tier, DEFAULT_TIER_CONFIGS[RateLimitTier.FREE])


def clear_all_policies() -> None:
    """Clear all policy configurations."""
    _org_policies.clear()
    _policy_cache.clear()
    PolicyLimitManager.reset_all_limits()


def get_policy_stats() -> Dict:
    """Get statistics about loaded policies."""
    total_orgs = len(_org_policies)
    total_restrictions = sum(
        len(p.restrictions) for p in _org_policies.values()
    )
    denied_policies = sum(
        1 for p in _org_policies.values()
        for allowed in p.restrictions.values()
        if not allowed
    )

    return {
        "total_organizations": total_orgs,
        "total_restrictions": total_restrictions,
        "denied_policies": denied_policies,
        "allowed_policies": total_restrictions - denied_policies,
        "essential_traffic_only": _is_essential_traffic_only,
    }


def export_policies() -> Dict[str, Dict]:
    """Export all policies for backup or transfer."""
    return {
        org_id: {
            "policy_type": config.policy_type.value,
            "enabled": config.enabled,
            "restrictions": config.restrictions,
            "updated_at": config.updated_at.isoformat(),
            "updated_by": config.updated_by,
        }
        for org_id, config in _org_policies.items()
    }


def import_policies(policies_data: Dict[str, Dict]) -> int:
    """Import policies from backup data. Returns count imported."""
    count = 0
    for org_id, data in policies_data.items():
        restrictions = {
            k: {"allowed": v} if isinstance(v, bool) else v
            for k, v in data.get("restrictions", {}).items()
        }
        load_policy_config(org_id, restrictions)
        count += 1
    return count
