"""
Policy Limits Service - Stub Module

This module has been expanded into a package at policy_limits/
Please use the new package structure:

    from api_server.services.policy_limits import (
        PolicyLimitManager,
        RateLimiter,
        QuotaManager,
        ViolationHandler,
        config,
        types,
    )

Or import directly from submodules:

    from api_server.services.policy_limits.limits import PolicyLimitManager
    from api_server.services.policy_limits.rate_limiting import RateLimiter
    from api_server.services.policy_limits.quota import QuotaManager
    from api_server.services.policy_limits.violations import ViolationHandler
    from api_server.services.policy_limits.config import load_policy_config, get_policy_for_org, update_policy
"""

from api_server.services.policy_limits import (
    PolicyLimitManager,
    RateLimiter,
    QuotaManager,
    ViolationHandler,
    config,
    types,
)

__all__ = [
    "PolicyLimitManager",
    "RateLimiter",
    "QuotaManager",
    "ViolationHandler",
    "config",
    "types",
]
