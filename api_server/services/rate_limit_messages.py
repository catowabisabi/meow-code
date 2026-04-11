from dataclasses import dataclass
from typing import Optional, List


@dataclass
class RateLimitMessage:
    message: str
    suggestion: Optional[str] = None


RATE_LIMIT_MESSAGES = {
    "requests_per_minute": RateLimitMessage(
        message="You've hit the rate limit for requests per minute. Please wait before trying again.",
        suggestion="Try batching your requests or using async operations.",
    ),
    "tokens_per_hour": RateLimitMessage(
        message="You've exceeded your token usage for this hour.",
        suggestion="Consider using shorter prompts or compressing context.",
    ),
    "concurrent_sessions": RateLimitMessage(
        message="You've reached the maximum number of concurrent sessions.",
        suggestion="Close some sessions before starting a new one.",
    ),
    "daily_limit": RateLimitMessage(
        message="You've reached your daily usage limit.",
        suggestion="Check back tomorrow or upgrade your plan.",
    ),
}


class RateLimitMessagesService:
    _custom_messages: dict = {}
    
    @classmethod
    def get_message(cls, limit_type: str) -> RateLimitMessage:
        return cls._custom_messages.get(limit_type) or RATE_LIMIT_MESSAGES.get(limit_type)
    
    @classmethod
    def set_custom_message(cls, limit_type: str, message: RateLimitMessage) -> None:
        cls._custom_messages[limit_type] = message
    
    @classmethod
    def get_optimization_tip(cls, limit_type: str) -> Optional[str]:
        msg = cls.get_message(limit_type)
        return msg.suggestion if msg else None
    
    @classmethod
    def get_all_messages(cls) -> dict:
        all_messages = RATE_LIMIT_MESSAGES.copy()
        all_messages.update(cls._custom_messages)
        return all_messages