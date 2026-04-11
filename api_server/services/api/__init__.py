"""
API service module for interacting with Anthropic Claude API.

Provides multi-provider support (Direct/Bedrock/Vertex/Foundry),
streaming and non-streaming query methods, retry logic, error handling,
usage tracking, and logging utilities.
"""

from .client import (
    get_anthropic_client,
    ApiClientConfig,
)

from .claude import (
    query_model_with_streaming,
    query_model_without_streaming,
    verify_api_key,
    QueryModelOptions,
    StreamingQueryResult,
)

from .with_retry import (
    with_retry,
    CannotRetryError,
    FallbackTriggeredError,
    RetryContext,
)

from .errors import (
    classify_api_error,
    get_assistant_message_from_error,
    API_ERROR_MESSAGE_PREFIX,
    PROMPT_TOO_LONG_ERROR_MESSAGE,
    INVALID_API_KEY_ERROR_MESSAGE,
    TOKEN_REVOKED_ERROR_MESSAGE,
    REPEATED_529_ERROR_MESSAGE,
    is_prompt_too_long_message,
    is_media_size_error,
    parse_prompt_too_long_token_counts,
)

from .usage import (
    fetch_utilization,
    RateLimit,
    ExtraUsage,
    Utilization,
)

from .logging import (
    log_api_query,
    log_api_error,
    log_api_success,
    log_api_success_and_duration,
    EMPTY_USAGE,
    GlobalCacheStrategy,
)

__all__ = [
    # client
    "get_anthropic_client",
    "ApiClientConfig",
    # claude
    "query_model_with_streaming",
    "query_model_without_streaming",
    "verify_api_key",
    "QueryModelOptions",
    "StreamingQueryResult",
    # with_retry
    "with_retry",
    "CannotRetryError",
    "FallbackTriggeredError",
    "RetryContext",
    # errors
    "classify_api_error",
    "get_assistant_message_from_error",
    "API_ERROR_MESSAGE_PREFIX",
    "PROMPT_TOO_LONG_ERROR_MESSAGE",
    "INVALID_API_KEY_ERROR_MESSAGE",
    "TOKEN_REVOKED_ERROR_MESSAGE",
    "REPEATED_529_ERROR_MESSAGE",
    "is_prompt_too_long_message",
    "is_media_size_error",
    "parse_prompt_too_long_token_counts",
    # usage
    "fetch_utilization",
    "RateLimit",
    "ExtraUsage",
    "Utilization",
    # logging
    "log_api_query",
    "log_api_error",
    "log_api_success",
    "log_api_success_and_duration",
    "EMPTY_USAGE",
    "GlobalCacheStrategy",
]
