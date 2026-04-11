from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional, Any, Dict
import asyncio
import logging

from .headers import (
    extract_all_rate_limit_info,
    parse_standard_rate_limit_headers,
    parse_anthropic_rate_limit_headers,
)


class QuotaStatus(str, Enum):
    ALLOWED = "allowed"
    ALLOWED_WARNING = "allowed_warning"
    REJECTED = "rejected"


class RateLimitType(str, Enum):
    FIVE_HOUR = "five_hour"
    SEVEN_DAY = "seven_day"
    SEVEN_DAY_OPUS = "seven_day_opus"
    SEVEN_DAY_SONNET = "seven_day_sonnet"
    OVERAGE = "overage"


class OverageDisabledReason(str, Enum):
    OVERAGE_NOT_PROVISIONED = "overage_not_provisioned"
    ORG_LEVEL_DISABLED = "org_level_disabled"
    ORG_LEVEL_DISABLED_UNTIL = "org_level_disabled_until"
    OUT_OF_CREDITS = "out_of_credits"
    SEAT_TIER_LEVEL_DISABLED = "seat_tier_level_disabled"
    MEMBER_LEVEL_DISABLED = "member_level_disabled"
    SEAT_TIER_ZERO_CREDIT_LIMIT = "seat_tier_zero_credit_limit"
    GROUP_ZERO_CREDIT_LIMIT = "group_zero_credit_limit"
    MEMBER_ZERO_CREDIT_LIMIT = "member_zero_credit_limit"
    ORG_SERVICE_LEVEL_DISABLED = "org_service_level_disabled"
    ORG_SERVICE_ZERO_CREDIT_LIMIT = "org_service_zero_credit_limit"
    NO_LIMITS_CONFIGURED = "no_limits_configured"
    UNKNOWN = "unknown"


RATE_LIMIT_DISPLAY_NAMES = {
    RateLimitType.FIVE_HOUR: "session limit",
    RateLimitType.SEVEN_DAY: "weekly limit",
    RateLimitType.SEVEN_DAY_OPUS: "Opus limit",
    RateLimitType.SEVEN_DAY_SONNET: "Sonnet limit",
    RateLimitType.OVERAGE: "extra usage limit",
}

CLAIM_ABBREV_TO_TYPE = {
    "5h": RateLimitType.FIVE_HOUR,
    "7d": RateLimitType.SEVEN_DAY,
    "overage": RateLimitType.OVERAGE,
}


@dataclass
class RateLimitInfo:
    limit_type: str
    used: int
    limit: int
    remaining: int
    reset_at: Optional[datetime] = None
    is_overage: bool = False
    status: QuotaStatus = QuotaStatus.ALLOWED
    utilization: Optional[float] = None
    overage_status: Optional[QuotaStatus] = None
    overage_reset_at: Optional[datetime] = None
    overage_disabled_reason: Optional[str] = None
    surpassed_threshold: Optional[float] = None
    fallback_available: bool = False

    @property
    def utilization_ratio(self) -> float:
        if self.limit <= 0:
            return 0.0
        return self.used / self.limit

    @property
    def reset_in_seconds(self) -> Optional[int]:
        if self.reset_at is None:
            return None
        now = datetime.now(timezone.utc)
        if self.reset_at.tzinfo is None:
            self.reset_at = self.reset_at.replace(tzinfo=timezone.utc)
        delta = self.reset_at - now
        return max(0, int(delta.total_seconds()))

    @property
    def is_exceeded(self) -> bool:
        return self.status == QuotaStatus.REJECTED or self.remaining <= 0


class RateLimitHandler:
    def __init__(self):
        self.current_limits: Optional[RateLimitInfo] = None
        self._last_error: Optional[Exception] = None
        self._retry_count: int = 0
        self._max_retries: int = 3
        self._base_backoff_seconds: float = 1.0
        self._logger = logging.getLogger(__name__)

    def parse_rate_limit_headers(self, headers: Dict[str, Any]) -> Optional[RateLimitInfo]:
        standard_info = parse_standard_rate_limit_headers(headers)
        anthropic_info = parse_anthropic_rate_limit_headers(headers)
        all_info = {**standard_info, **anthropic_info}
        if not all_info:
            return None
        status_str = all_info.get("status", "allowed")
        try:
            status = QuotaStatus(status_str)
        except ValueError:
            status = QuotaStatus.ALLOWED
        limit_type = all_info.get("rate_limit_type", "unknown")
        if isinstance(limit_type, str) and limit_type in [
            "five_hour",
            "seven_day",
            "seven_day_opus",
            "seven_day_sonnet",
            "overage",
        ]:
            limit_type_value = limit_type
        else:
            limit_type_value = "unknown"
        used = 0
        limit = 0
        remaining = 0
        utilization = None
        if "limit" in all_info:
            limit = all_info["limit"]
            remaining = all_info.get("remaining", limit)
            used = limit - remaining
        if "five_hour" in all_info:
            util_data = all_info["five_hour"]
            if util_data and "utilization" in util_data:
                utilization = util_data["utilization"]
                used = int(utilization * 100)
                limit = 100
                remaining = max(0, limit - used)
                limit_type_value = "five_hour"
        elif "seven_day" in all_info:
            util_data = all_info["seven_day"]
            if util_data and "utilization" in util_data:
                utilization = util_data["utilization"]
                used = int(utilization * 100)
                limit = 100
                remaining = max(0, limit - used)
                limit_type_value = "seven_day"
        if limit_type_value == "unknown" and "limit_type" in all_info:
            std_type = all_info.get("limit_type", "")
            if std_type in ("5m", "5h"):
                limit_type_value = "five_hour"
            elif std_type in ("1h", "1d"):
                limit_type_value = "seven_day"
        reset_at = all_info.get("reset_at")
        overage_status_str = all_info.get("overage_status")
        overage_status = None
        if overage_status_str:
            try:
                overage_status = QuotaStatus(overage_status_str)
            except ValueError:
                pass
        overage_reset_at = all_info.get("overage_reset_at")
        is_overage = status == QuotaStatus.REJECTED and (
            overage_status == QuotaStatus.ALLOWED
            or overage_status == QuotaStatus.ALLOWED_WARNING
        )
        info = RateLimitInfo(
            limit_type=limit_type_value,
            used=used,
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
            is_overage=is_overage,
            status=status,
            utilization=utilization,
            overage_status=overage_status,
            overage_reset_at=overage_reset_at,
            overage_disabled_reason=all_info.get("overage_disabled_reason"),
            surpassed_threshold=all_info.get("five_hour", {}).get(
                "surpassed_threshold"
            )
            or all_info.get("seven_day", {}).get("surpassed_threshold"),
            fallback_available=all_info.get("fallback_available", False),
        )
        self.current_limits = info
        return info

    def parse_quota_from_error(self, error_response: Dict[str, Any]) -> Optional[RateLimitInfo]:
        if isinstance(error_response, dict):
            headers = error_response.get("headers", error_response)
        else:
            headers = {}
        if "X-RateLimit-Limit" in headers or "anthropic-ratelimit-unified-status" in headers:
            return self.parse_rate_limit_headers(headers)
        error_msg = error_response.get("message", "") if isinstance(error_response, dict) else str(error_response)
        if "429" in str(error_msg) or "rate limit" in error_msg.lower():
            return RateLimitInfo(
                limit_type="unknown",
                used=0,
                limit=0,
                remaining=0,
                status=QuotaStatus.REJECTED,
            )
        return None

    async def handle_rate_limit_error(
        self,
        error: Exception,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._last_error = error
        self._retry_count = 0
        retry_after = self.get_retry_after_seconds()
        if retry_after is None:
            retry_after = self._calculate_backoff()
        if on_progress:
            message = self.get_user_message()
            on_progress(message)
        while self._retry_count < self._max_retries:
            self._retry_count += 1
            wait_time = retry_after * (2 ** (self._retry_count - 1))
            wait_time = min(wait_time, 60)
            if on_progress:
                progress_msg = f"Rate limit hit. Retry {self._retry_count}/{self._max_retries} in {wait_time} seconds..."
                on_progress(progress_msg)
            await asyncio.sleep(wait_time)
            retry_after = self._calculate_backoff()
        if self._retry_count >= self._max_retries:
            if on_progress:
                on_progress("Max retries exceeded for rate limit. Please try again later.")

    def _calculate_backoff(self) -> int:
        if self.current_limits and self.current_limits.reset_in_seconds:
            return self.current_limits.reset_in_seconds
        base = self._base_backoff_seconds
        if self._retry_count > 0:
            return int(min(base * (2 ** self._retry_count), 60))
        return int(base)

    def get_retry_after_seconds(self) -> Optional[int]:
        if self.current_limits:
            if self.current_limits.reset_in_seconds is not None:
                return self.current_limits.reset_in_seconds
            if self.current_limits.overage_reset_at:
                now = datetime.now(timezone.utc)
                if self.current_limits.overage_reset_at.tzinfo is None:
                    self.current_limits.overage_reset_at = (
                        self.current_limits.overage_reset_at.replace(
                            tzinfo=timezone.utc
                        )
                    )
                delta = self.current_limits.overage_reset_at - now
                return max(0, int(delta.total_seconds()))
        return None

    def get_user_message(self) -> str:
        if not self.current_limits:
            return "Rate limit error occurred. Please try again later."
        limits = self.current_limits
        display_name = RATE_LIMIT_DISPLAY_NAMES.get(
            RateLimitType(limits.limit_type)
            if limits.limit_type in [e.value for e in RateLimitType]
            else RateLimitType.FIVE_HOUR,
            "usage limit",
        )
        if limits.is_overage:
            if limits.overage_status == QuotaStatus.ALLOWED_WARNING:
                return "You're close to your extra usage spending limit."
            return "Now using extra usage."
        if limits.status == QuotaStatus.REJECTED:
            reset_in = limits.reset_in_seconds
            if reset_in is not None:
                if reset_in < 60:
                    reset_text = f"Wait {reset_in} seconds"
                elif reset_in < 3600:
                    reset_text = f"Wait {reset_in // 60} minutes"
                else:
                    reset_text = f"Resets in {reset_in // 3600} hours"
                return f"You've hit your {display_name}. {reset_text}."
            return f"You've hit your {display_name}."
        if limits.status == QuotaStatus.ALLOWED_WARNING:
            util_pct = int(limits.utilization * 100) if limits.utilization else None
            if util_pct is not None and limits.reset_at:
                reset_in = limits.reset_in_seconds
                if reset_in is not None:
                    if reset_in < 3600:
                        reset_text = f"resets in {reset_in // 60} minutes"
                    else:
                        reset_text = f"resets in {reset_in // 3600} hours"
                    return f"You've used {util_pct}% of your {display_name} · {reset_text}"
                return f"You've used {util_pct}% of your {display_name}"
            if limits.reset_at:
                reset_in = limits.reset_in_seconds
                if reset_in is not None:
                    if reset_in < 3600:
                        reset_text = f"resets in {reset_in // 60} minutes"
                    else:
                        reset_text = f"resets in {reset_in // 3600} hours"
                    return f"Approaching {display_name} · {reset_text}"
            return f"Approaching {display_name}"
        if limits.remaining <= 0:
            reset_in = limits.reset_in_seconds
            if reset_in is not None:
                if reset_in < 3600:
                    reset_text = f"Wait {reset_in // 60} minutes"
                else:
                    reset_text = f"Resets in {reset_in // 3600} hours"
                return f"You've hit your {display_name}. {reset_text}."
            return f"You've hit your {display_name}."
        return "Rate limit status unknown."

    def get_status_summary(self) -> Dict[str, Any]:
        if not self.current_limits:
            return {"status": "unknown", "message": "No rate limit information available."}
        return {
            "status": self.current_limits.status.value,
            "limit_type": self.current_limits.limit_type,
            "remaining": self.current_limits.remaining,
            "is_overage": self.current_limits.is_overage,
            "message": self.get_user_message(),
        }

    def reset(self) -> None:
        self.current_limits = None
        self._last_error = None
        self._retry_count = 0
