"""Header parsing utilities for rate limit extraction."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any


STANDARD_RATE_LIMIT_HEADERS = [
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
    "X-RateLimit-Type",
    "Retry-After",
]


ANTHROPIC_RATE_LIMIT_HEADERS = [
    "anthropic-ratelimit-unified-status",
    "anthropic-ratelimit-unified-reset",
    "anthropic-ratelimit-unified-fallback",
    "anthropic-ratelimit-unified-representative-claim",
    "anthropic-ratelimit-unified-overage-status",
    "anthropic-ratelimit-unified-overage-reset",
    "anthropic-ratelimit-unified-overage-disabled-reason",
]


ANTHROPIC_UTILIZATION_HEADERS = [
    "anthropic-ratelimit-unified-5h-utilization",
    "anthropic-ratelimit-unified-7d-utilization",
    "anthropic-ratelimit-unified-5h-reset",
    "anthropic-ratelimit-unified-7d-reset",
    "anthropic-ratelimit-unified-5h-surpassed-threshold",
    "anthropic-ratelimit-unified-7d-surpassed-threshold",
]


def get_header_value(headers: Dict[str, Any], key: str) -> Optional[str]:
    if isinstance(headers, dict):
        return headers.get(key) or headers.get(key.lower()) or headers.get(key.upper())
    if hasattr(headers, "get"):
        return headers.get(key) or headers.get(key.lower()) or headers.get(key.upper())
    return None


def parse_int_header(headers: Dict[str, Any], key: str) -> Optional[int]:
    value = get_header_value(headers, key)
    if value is not None:
        try:
            return int(value)
        except (ValueError, TypeError):
            pass
    return None


def parse_float_header(headers: Dict[str, Any], key: str) -> Optional[float]:
    value = get_header_value(headers, key)
    if value is not None:
        try:
            return float(value)
        except (ValueError, TypeError):
            pass
    return None


def parse_timestamp_to_datetime(timestamp: Optional[int]) -> Optional[datetime]:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def parse_retry_after_header(headers: Dict[str, Any]) -> Optional[int]:
    retry_after = get_header_value(headers, "Retry-After")
    if retry_after is not None:
        try:
            return int(retry_after)
        except (ValueError, TypeError):
            pass
    retry_date = get_header_value(headers, "Retry-After")
    if retry_date:
        try:
            dt = datetime.strptime(retry_date, "%a, %d %b %Y %H:%M:%S GMT")
            delta = dt - datetime.utcnow()
            return max(1, int(delta.total_seconds()))
        except (ValueError, TypeError):
            pass
    return None


def parse_standard_rate_limit_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    limit = parse_int_header(headers, "X-RateLimit-Limit")
    if limit is not None:
        result["limit"] = limit
    remaining = parse_int_header(headers, "X-RateLimit-Remaining")
    if remaining is not None:
        result["remaining"] = remaining
    reset_timestamp = parse_int_header(headers, "X-RateLimit-Reset")
    if reset_timestamp is not None:
        result["reset_at"] = parse_timestamp_to_datetime(reset_timestamp)
        result["reset_timestamp"] = reset_timestamp
    limit_type = get_header_value(headers, "X-RateLimit-Type")
    if limit_type is not None:
        result["limit_type"] = limit_type
    retry_after = parse_retry_after_header(headers)
    if retry_after is not None:
        result["retry_after_seconds"] = retry_after
    return result


def parse_anthropic_status_header(headers: Dict[str, Any]) -> Optional[str]:
    status = get_header_value(headers, "anthropic-ratelimit-unified-status")
    if status in ("allowed", "allowed_warning", "rejected"):
        return status
    return None


def parse_anthropic_reset_header(headers: Dict[str, Any]) -> Optional[datetime]:
    reset_timestamp = parse_int_header(headers, "anthropic-ratelimit-unified-reset")
    return parse_timestamp_to_datetime(reset_timestamp)


def parse_anthropic_utilization(
    headers: Dict[str, Any], claim_abbrev: str
) -> Optional[Dict[str, Any]]:
    util_key = f"anthropic-ratelimit-unified-{claim_abbrev}-utilization"
    reset_key = f"anthropic-ratelimit-unified-{claim_abbrev}-reset"
    surpassed_key = f"anthropic-ratelimit-unified-{claim_abbrev}-surpassed-threshold"
    utilization = parse_float_header(headers, util_key)
    reset_timestamp = parse_int_header(headers, reset_key)
    surpassed_threshold = parse_int_header(headers, surpassed_key)
    if utilization is not None and reset_timestamp is not None:
        return {
            "utilization": utilization,
            "resets_at": parse_timestamp_to_datetime(reset_timestamp),
            "surpassed_threshold": surpassed_threshold,
        }
    return None


def parse_anthropic_rate_limit_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    status = parse_anthropic_status_header(headers)
    if status is not None:
        result["status"] = status
    reset_at = parse_anthropic_reset_header(headers)
    if reset_at is not None:
        result["reset_at"] = reset_at
    fallback = get_header_value(headers, "anthropic-ratelimit-unified-fallback")
    if fallback is not None:
        result["fallback_available"] = fallback == "available"
    representative_claim = get_header_value(
        headers, "anthropic-ratelimit-unified-representative-claim"
    )
    if representative_claim is not None:
        result["rate_limit_type"] = representative_claim
    overage_status = get_header_value(
        headers, "anthropic-ratelimit-unified-overage-status"
    )
    if overage_status in ("allowed", "allowed_warning", "rejected"):
        result["overage_status"] = overage_status
    overage_reset = parse_int_header(
        headers, "anthropic-ratelimit-unified-overage-reset"
    )
    if overage_reset is not None:
        result["overage_reset_at"] = parse_timestamp_to_datetime(overage_reset)
    overage_disabled_reason = get_header_value(
        headers, "anthropic-ratelimit-unified-overage-disabled-reason"
    )
    if overage_disabled_reason is not None:
        result["overage_disabled_reason"] = overage_disabled_reason
    five_hour_util = parse_anthropic_utilization(headers, "5h")
    if five_hour_util is not None:
        result["five_hour"] = five_hour_util
    seven_day_util = parse_anthropic_utilization(headers, "7d")
    if seven_day_util is not None:
        result["seven_day"] = seven_day_util
    return result


def extract_all_rate_limit_info(headers: Dict[str, Any]) -> Dict[str, Any]:
    standard = parse_standard_rate_limit_headers(headers)
    anthropic = parse_anthropic_rate_limit_headers(headers)
    merged = {**standard, **anthropic}
    return merged
