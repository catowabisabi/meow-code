import asyncio
import os
import random
from dataclasses import dataclass, field
from typing import Optional, Any, AsyncGenerator, Callable, Awaitable, Dict

from .errors import REPEATED_529_ERROR_MESSAGE


BASE_DELAY_MS = 500
DEFAULT_MAX_RETRIES = 10
MAX_529_RETRIES = 3
FLOOR_OUTPUT_TOKENS = 3000


@dataclass
class RetryContext:
    model: str
    thinking_config: dict = field(default_factory=dict)
    fast_mode: Optional[bool] = None
    max_tokens_override: Optional[int] = None


class CannotRetryError(Exception):
    def __init__(self, original_error: Any, retry_context: RetryContext):
        self.original_error = original_error
        self.retry_context = retry_context
        message = str(original_error) if original_error else "Unknown error"
        super().__init__(message)
        self.name = "CannotRetryError"


class FallbackTriggeredError(Exception):
    def __init__(self, original_model: str, fallback_model: str):
        self.original_model = original_model
        self.fallback_model = fallback_model
        super().__init__(f"Model fallback triggered: {original_model} -> {fallback_model}")
        self.name = "FallbackTriggeredError"


def _is_env_truthy(env_var: Optional[str]) -> bool:
    if not env_var:
        return False
    return env_var.lower() in ("true", "1", "yes")


def _is_529_error(error: Any) -> bool:
    if not isinstance(error, dict):
        return False
    status = error.get("status")
    if status == 529:
        return True
    message = error.get("message", "")
    if isinstance(message, str) and '"type":"overloaded_error"' in message:
        return True
    return False


def _is_oauth_token_revoked_error(error: Any) -> bool:
    if not isinstance(error, dict):
        return False
    status = error.get("status")
    message = error.get("message", "")
    return status == 403 and "OAuth token has been revoked" in message


def _is_bedrock_auth_error(error: Any) -> bool:
    if not _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_BEDROCK")):
        return False
    if isinstance(error, dict):
        status = error.get("status")
        if status == 403:
            return True
        error_type = error.get("type", "")
        if "CredentialsProviderError" in error_type:
            return True
    return False


def _is_vertex_auth_error(error: Any) -> bool:
    if not _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_VERTEX")):
        return False
    if isinstance(error, dict):
        if error.get("status") == 401:
            return True
        message = str(error.get("message", ""))
        if "Could not load the default credentials" in message:
            return True
        if "Could not refresh access token" in message:
            return True
        if "invalid_grant" in message:
            return True
    return False


def _should_retry(error: Any) -> bool:
    if not isinstance(error, dict):
        return False
    
    status = error.get("status")
    message = error.get("message", "")
    
    if status == 408:
        return True
    if status == 409:
        return True
    if status == 429:
        return True
    if status == 401:
        return True
    if status == 403 and "OAuth token has been revoked" in message:
        return True
    if status and status >= 500:
        return True
    if '"type":"overloaded_error"' in message:
        return True
    
    return False


def _get_retry_after(error: Any) -> Optional[str]:
    if isinstance(error, dict):
        headers = error.get("headers", {})
        if isinstance(headers, dict):
            return headers.get("retry-after")
        if hasattr(headers, "get"):
            return headers.get("retry-after")
    return None


def _get_retry_delay(
    attempt: int,
    retry_after_header: Optional[str] = None,
    max_delay_ms: int = 32000,
) -> float:
    if retry_after_header:
        try:
            seconds = int(retry_after_header)
            if seconds > 0:
                return seconds * 1000
        except ValueError:
            pass
    
    base_delay = min(BASE_DELAY_MS * (2 ** (attempt - 1)), max_delay_ms)
    jitter = random.random() * 0.25 * base_delay
    return base_delay + jitter


async def _sleep(ms: float, signal: Optional[Any] = None) -> None:
    remaining = ms
    while remaining > 0:
        if signal is not None and getattr(signal, "aborted", False):
            break
        chunk = min(remaining, 100)
        await asyncio.sleep(chunk / 1000)
        remaining -= chunk


async def with_retry(
    get_client: Callable[[], Awaitable[Any]],
    operation: Callable[[Any, int, RetryContext], Awaitable[Any]],
    options: Optional[dict] = None,
) -> AsyncGenerator[Dict[str, Any], Any]:
    """
    Async generator with exponential backoff retry logic.
    
    Handles 529 (Overloaded) errors specially with max 3 retries.
    Handles credential refresh on 401/403.
    """
    options = options or {}
    max_retries = options.get("max_retries", DEFAULT_MAX_RETRIES)
    model = options.get("model", "")
    fallback_model = options.get("fallback_model")
    thinking_config = options.get("thinking_config", {})
    signal = options.get("signal")
    options.get("query_source")
    initial_consecutive_529_errors = options.get("initial_consecutive_529_errors", 0)
    
    retry_context = RetryContext(
        model=model,
        thinking_config=thinking_config,
        fast_mode=options.get("fast_mode"),
    )
    
    client = None
    consecutive_529_errors = initial_consecutive_529_errors
    last_error = None
    
    for attempt in range(1, max_retries + 2):
        if signal is not None and getattr(signal, "aborted", False):
            yield {"type": "abort"}
            return
        
        should_refresh_client = (
            client is None or
            (isinstance(last_error, dict) and last_error.get("status") == 401) or
            _is_oauth_token_revoked_error(last_error) or
            _is_bedrock_auth_error(last_error) or
            _is_vertex_auth_error(last_error)
        )
        
        if should_refresh_client:
            client = await get_client()
        
        try:
            result = await operation(client, attempt, retry_context)
            yield {"type": "result", "value": result}
            return
        except Exception as e:
            last_error = _parse_error(e)
            
            if _is_529_error(last_error):
                consecutive_529_errors += 1
                
                if consecutive_529_errors >= MAX_529_RETRIES:
                    if fallback_model:
                        raise FallbackTriggeredError(model, fallback_model)
                    
                    if os.environ.get("USER_TYPE") == "external":
                        if not _is_env_truthy(os.environ.get("CLAUDE_CODE_UNATTENDED_RETRY")):
                            raise CannotRetryError(
                                Exception(REPEATED_529_ERROR_MESSAGE),
                                retry_context,
                            )
            
            if not _should_retry(last_error):
                if _is_529_error(last_error):
                    consecutive_529_errors = max(0, consecutive_529_errors - 1)
                raise CannotRetryError(e, retry_context)
        
        retry_after = _get_retry_after(last_error)
        delay_ms = _get_retry_delay(attempt, retry_after)
        
        yield {
            "type": "retry",
            "delay_ms": delay_ms,
            "attempt": attempt,
            "max_retries": max_retries,
            "error": last_error,
        }
        
        await _sleep(delay_ms, signal)
    
    raise CannotRetryError(last_error, retry_context)


def _parse_error(error: Exception) -> dict:
    if isinstance(error, dict):
        return error
    
    status = getattr(error, "status", None)
    message = str(error)
    error_type = type(error).__name__
    
    result = {
        "type": error_type,
        "message": message,
    }
    
    if status is not None:
        result["status"] = status
    
    headers = getattr(error, "headers", None)
    if headers is not None:
        if hasattr(headers, "get"):
            result["headers"] = {
                "retry-after": headers.get("retry-after"),
                "anthropic-ratelimit-unified-reset": headers.get("anthropic-ratelimit-unified-reset"),
            }
        elif isinstance(headers, dict):
            result["headers"] = headers
    
    return result
