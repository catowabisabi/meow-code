"""Rate limit handling for API responses.

This module provides rate limit detection, parsing, and handling for
Claude API responses. It supports:
- Standard X-RateLimit headers
- Claude-specific anthropic-ratelimit-unified-* headers
- Quota status tracking (allowed, allowed_warning, rejected)
- Automatic retry with backoff
- User-friendly message generation
"""

from .rate_limit_handler import (
    RateLimitInfo,
    RateLimitHandler,
    QuotaStatus,
    RateLimitType,
    OverageDisabledReason,
)

__all__ = [
    "RateLimitInfo",
    "RateLimitHandler",
    "QuotaStatus",
    "RateLimitType",
    "OverageDisabledReason",
]
