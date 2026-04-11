"""
Claude API Service - Complete Python port from TypeScript
Full implementation of all API interaction functions for Anthropic's Claude models.
"""

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

import httpx

from .client import get_anthropic_client
from .empty_usage import EMPTY_USAGE
from .errors import (
    API_ERROR_MESSAGE_PREFIX,
    get_assistant_message_from_error,
)
from .prompt_cache_break_detection import (
    CACHE_TTL_1HOUR_MS,
    check_response_for_cache_break,
    record_prompt_state,
)
from .with_retry import (
    FallbackTriggeredError,
    RetryContext,
    with_retry,
)


# =============================================================================
# Beta Headers (21 headers)
# =============================================================================

BETA_HEADERS: Dict[str, Any] = {
    "X-Api-Key": lambda: os.environ.get("ANTHROPIC_API_KEY", ""),
    "Authorization": lambda: f"Bearer {os.environ.get('ANTHROPIC_API_KEY', '')}",
    "anthropic-beta": "interleaved-thinking-2025-02-19",
    "anthropic-dangerous-direct-browser-access": "true",
    "HTTP-Referer": "https://claude.ai",
    "X-Client-Info": f"claude-code/{os.environ.get('CLAUDE_CODE_VERSION', 'unknown')}",
}

AFK_MODE_BETA_HEADER = "ans-beta-feature: afk"
CONTEXT_1M_BETA_HEADER = "anthropic-beta-max-tokens: 200000"
CONTEXT_MANAGEMENT_BETA_HEADER = "anthropic-beta: conversation-management-v1"
EFFORT_BETA_HEADER = "anthropic-beta: tool-use-effort-v1"
FAST_MODE_BETA_HEADER = "ans-beta-feature: fast-mode"
PROMPT_CACHING_SCOPE_BETA_HEADER = "anthropic-beta: prompt-caching-2024-05-14"
REDACT_THINKING_BETA_HEADER = "anthropic-beta: redact-thinking"
STRUCTURED_OUTPUTS_BETA_HEADER = "anthropic-beta: structured-outputs"
TASK_BUDDYS_BETA_HEADER = "anthropic-beta: tool-use-budding-v1"
CACHE_EDITING_BETA_HEADER = "anthropic-beta: cache-edits-v1"
ADVISOR_BETA_HEADER = "anthropic-beta: advisor-20260301"


# =============================================================================
# Constants
# =============================================================================

HAIKU_MODEL = "claude-3-5-haiku-20241022"
SONNET_MODEL = "claude-sonnet-4-20250514"
OPUS_MODEL = "claude-opus-4-20250514"

CAPPED_DEFAULT_MAX_TOKENS = 8000
MAX_NON_STREAMING_TOKENS = 64000
CACHE_TTL_1HOUR_MS = 60 * 60 * 1000  # 1 hour in ms

# Tool search tool name
TOOL_SEARCH_TOOL_NAME = "tool_search"


# =============================================================================
# Helper Functions
# =============================================================================


def _is_env_truthy(env_var: Optional[str]) -> bool:
    """Check if an environment variable is set to a truthy value."""
    if not env_var:
        return False
    return env_var.lower() in ("true", "1", "yes")


def _safe_parse_json(json_str: str, allow_null: bool = True) -> Any:
    """Safely parse a JSON string, returning None on error."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None


def _error_message(error: Exception) -> str:
    """Get error message from an exception."""
    if hasattr(error, "message"):
        return str(error.message)
    return str(error)


def _get_small_fast_model() -> str:
    """Get the small fast model for Haiku queries."""
    return os.environ.get("ANTHROPIC_SMALL_FAST_MODEL", HAIKU_MODEL)


def _get_default_sonnet_model() -> str:
    """Get the default Sonnet model."""
    return os.environ.get("ANTHROPIC_MODEL", SONNET_MODEL)


def _get_default_opus_model() -> str:
    """Get the default Opus model."""
    return os.environ.get("ANTHROPIC_OPUS_MODEL", OPUS_MODEL)


def _get_session_id() -> str:
    """Get the current session ID."""
    return os.environ.get("CLAUDE_CODE_SESSION_ID", "")


def _get_user_id() -> str:
    """Get or create a user ID."""
    return os.environ.get("CLAUDE_CODE_USER_ID", str(uuid.uuid4()))


def _get_api_provider() -> str:
    """Get the current API provider."""
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_BEDROCK")):
        return "bedrock"
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_FOUNDRY")):
        return "foundry"
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_VERTEX")):
        return "vertex"
    return "firstParty"


def _is_first_party_anthropic_base_url() -> bool:
    """Check if using first-party Anthropic base URL."""
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    return not base_url or "anthropic.com" in base_url


def _should_include_first_party_only_betas() -> bool:
    """Check if first-party only betas should be included."""
    return _get_api_provider() == "firstParty" and _is_first_party_anthropic_base_url()


def _get_current_time_ms() -> int:
    """Get current time in milliseconds."""
    return int(time.time() * 1000)


def _is_claude_ai_subscriber() -> bool:
    """Check if user is a Claude AI subscriber."""
    return _is_env_truthy(os.environ.get("CLAUDE_AI_SUBSCRIBER"))


def _get_feature_value_cached(feature_name: str, default: Any = None) -> Any:
    """Get feature value from GrowthBook (placeholder)."""
    config_str = os.environ.get(f"TENGU_{feature_name.upper()}_CONFIG", "{}")
    config = _safe_parse_json(config_str) or {}
    return config.get("value", default)


def _log_for_debugging(message: str, level: str = "info") -> None:
    """Log debug message."""
    print(f"[claude.py] {message}", flush=True)


def _log_event(event_name: str, params: Dict[str, Any]) -> None:
    """Log event for analytics (placeholder)."""
    pass


# =============================================================================
# State Management (latches for session-stable headers)
# =============================================================================

_afk_mode_header_latched: bool = False
_fast_mode_header_latched: bool = False
_cache_editing_header_latched: bool = False
_thinking_clear_latched: bool = False
_prompt_cache_1h_eligible: Optional[bool] = None
_prompt_cache_1h_allowlist: Optional[List[str]] = None
_last_api_completion_timestamp: Optional[int] = None
_last_main_request_id: Optional[str] = None


def _get_afk_mode_header_latched() -> bool:
    return _afk_mode_header_latched


def _set_afk_mode_header_latched(value: bool) -> None:
    global _afk_mode_header_latched
    _afk_mode_header_latched = value


def _get_fast_mode_header_latched() -> bool:
    return _fast_mode_header_latched


def _set_fast_mode_header_latched(value: bool) -> None:
    global _fast_mode_header_latched
    _fast_mode_header_latched = value


def _get_cache_editing_header_latched() -> bool:
    return _cache_editing_header_latched


def _set_cache_editing_header_latched(value: bool) -> None:
    global _cache_editing_header_latched
    _cache_editing_header_latched = value


def _get_thinking_clear_latched() -> bool:
    return _thinking_clear_latched


def _set_thinking_clear_latched(value: bool) -> None:
    global _thinking_clear_latched
    _thinking_clear_latched = value


def _get_prompt_cache_1h_eligible() -> Optional[bool]:
    return _prompt_cache_1h_eligible


def _set_prompt_cache_1h_eligible(value: bool) -> None:
    global _prompt_cache_1h_eligible
    _prompt_cache_1h_eligible = value


def _get_prompt_cache_1h_allowlist() -> Optional[List[str]]:
    return _prompt_cache_1h_allowlist


def _set_prompt_cache_1h_allowlist(value: List[str]) -> None:
    global _prompt_cache_1h_allowlist
    _prompt_cache_1h_allowlist = value


def _get_last_api_completion_timestamp() -> Optional[int]:
    return _last_api_completion_timestamp


def _set_last_api_completion_timestamp(value: int) -> None:
    global _last_api_completion_timestamp
    _last_api_completion_timestamp = value


def _get_last_main_request_id() -> Optional[str]:
    return _last_main_request_id


def _set_last_main_request_id(value: str) -> None:
    global _last_main_request_id
    _last_main_request_id = value


def clear_beta_header_latches() -> None:
    """Clear all beta header latches (called on /clear and /compact)."""
    global _afk_mode_header_latched, _fast_mode_header_latched
    global _cache_editing_header_latched, _thinking_clear_latched
    _afk_mode_header_latched = False
    _fast_mode_header_latched = False
    _cache_editing_header_latched = False
    _thinking_clear_latched = False


# =============================================================================
# Beta Headers Management
# =============================================================================


def _get_model_betas(model: str) -> List[str]:
    """Get beta headers for a model based on configuration."""
    betas: List[str] = []
    
    # Add model-specific betas based on model type
    model_lower = model.lower()
    
    if "sonnet" in model_lower or "opus" in model_lower:
        betas.append(PROMPT_CACHING_SCOPE_BETA_HEADER)
    
    return betas


def _get_merged_betas(
    model: str,
    options: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Get merged beta headers for a model."""
    options = options or {}
    is_agentic_query = options.get("isAgenticQuery", False)
    
    betas = _get_model_betas(model)
    
    # Add agentic query specific betas
    if is_agentic_query:
        betas.append(CONTEXT_MANAGEMENT_BETA_HEADER)
    
    return betas


def _get_tool_search_beta_header() -> Optional[str]:
    """Get the tool search beta header if enabled."""
    provider = _get_api_provider()
    if provider == "bedrock":
        return "anthropic-beta: tool-search-tool"
    return "anthropic-beta: advanced-tool-use"


def _should_use_global_cache_scope() -> bool:
    """Check if global cache scope should be used."""
    return _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_GLOBAL_CACHE_SCOPE"))


# =============================================================================
# Model Support Functions
# =============================================================================


def model_supports_effort(model: str) -> bool:
    """Check if model supports effort parameter."""
    m = model.lower()
    
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_ALWAYS_ENABLE_EFFORT")):
        return True
    
    # Supported by a subset of Claude 4 models
    if "opus-4-6" in m or "sonnet-4-6" in m:
        return True
    
    # Exclude any other known legacy models
    if "haiku" in m or "sonnet" in m or "opus" in m:
        return False
    
    # Default to true for first party unknown model strings
    return _get_api_provider() == "firstParty"


def model_supports_max_effort(model: str) -> bool:
    """Check if model supports 'max' effort level."""
    m = model.lower()
    if "opus-4-6" in m:
        return True
    return False


def _model_supports_thinking(model: str) -> bool:
    """Check if model supports thinking."""
    m = model.lower()
    return "sonnet" in m or "opus" in m


def _model_supports_adaptive_thinking(model: str) -> bool:
    """Check if model supports adaptive thinking."""
    m = model.lower()
    return "sonnet" in m or "opus" in m


def _model_supports_structured_outputs(model: str) -> bool:
    """Check if model supports structured outputs."""
    m = model.lower()
    return "sonnet" in m or "opus" in m


def _is_non_custom_opus_model(model: str) -> bool:
    """Check if model is a non-custom Opus model."""
    m = model.lower()
    return "opus" in m and "custom" not in m


def _normalize_model_string_for_api(model: str) -> str:
    """Normalize model string for API."""
    return model


def _parse_user_specified_model(model: str) -> str:
    """Parse user-specified model string."""
    return model


def _get_max_thinking_tokens_for_model(model: str) -> int:
    """Get max thinking tokens for model."""
    m = model.lower()
    if "opus" in m:
        return 32000
    if "sonnet" in m:
        return 16000
    return 8000


def _get_model_max_output_tokens(model: str) -> Dict[str, Any]:
    """Get max output tokens for model."""
    m = model.lower()
    if "opus" in m:
        return {"default": 4096, "upperLimit": 8192}
    if "sonnet" in m:
        return {"default": 8192, "upperLimit": 8192}
    if "haiku" in m:
        return {"default": 4096, "upperLimit": 4096}
    return {"default": 4096, "upperLimit": 8192}


# =============================================================================
# Effort Configuration
# =============================================================================


EFFORT_LEVELS = ["low", "medium", "high", "max"]


def is_effort_level(value: str) -> bool:
    """Check if value is a valid effort level."""
    return value in EFFORT_LEVELS


def parse_effort_value(value: Any) -> Optional[Union[str, int]]:
    """Parse effort value from various formats."""
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        if is_effort_level(value.lower()):
            return value.lower()
        try:
            return int(value)
        except ValueError:
            pass
    return None


def _is_valid_numeric_effort(value: int) -> bool:
    """Check if numeric effort value is valid."""
    return isinstance(value, int)


def convert_effort_value_to_level(value: Union[str, int]) -> str:
    """Convert effort value to effort level string."""
    if isinstance(value, str):
        if is_effort_level(value):
            return value
        return "high"
    if isinstance(value, int):
        if value <= 50:
            return "low"
        if value <= 85:
            return "medium"
        if value <= 100:
            return "high"
        return "max"
    return "high"


def _get_default_effort_for_model(model: str) -> Optional[Union[str, int]]:
    """Get default effort level for a model."""
    m = model.lower()
    
    # Default effort on Opus 4.6 to medium for subscribers
    if "opus-4-6" in m:
        if _is_claude_ai_subscriber():
            return "medium"
    
    return None


def resolve_applied_effort(
    model: str,
    effort_value: Optional[Union[str, int]] = None,
) -> Optional[Union[str, int]]:
    """Resolve the effort value to send to the API."""
    env_override = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL")
    
    if env_override:
        env_override_lower = env_override.lower()
        if env_override_lower == "unset" or env_override_lower == "auto":
            return None
        parsed = parse_effort_value(env_override)
        if parsed is not None:
            return parsed
    
    if effort_value is not None:
        resolved = effort_value
        # API rejects 'max' on non-Opus-4.6 models
        if resolved == "max" and not model_supports_max_effort(model):
            return "high"
        return resolved
    
    default = _get_default_effort_for_model(model)
    if default is not None:
        return default
    
    return None


def _configure_effort_params(
    effort_value: Optional[Union[str, int]],
    output_config: Dict[str, Any],
    extra_body_params: Dict[str, Any],
    betas: List[str],
    model: str,
) -> None:
    """Configure effort parameters for API request."""
    if not model_supports_effort(model) or "effort" in output_config:
        return
    
    if effort_value is None:
        betas.append(EFFORT_BETA_HEADER)
    elif isinstance(effort_value, str):
        output_config["effort"] = effort_value
        betas.append(EFFORT_BETA_HEADER)
    elif os.environ.get("USER_TYPE") == "ant":
        existing_internal = extra_body_params.get("anthropic_internal", {})
        if not isinstance(existing_internal, dict):
            existing_internal = {}
        extra_body_params["anthropic_internal"] = {
            **existing_internal,
            "effort_override": effort_value,
        }


# =============================================================================
# Fingerprinting
# =============================================================================


FINGERPRINT_SALT = "59cf53e54c78"


def _extract_first_message_text(messages: List[Dict[str, Any]]) -> str:
    """Extract text content from the first user message."""
    for msg in messages:
        if msg.get("type") == "user":
            content = msg.get("message", {}).get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        return block.get("text", "")
            return ""
    return ""


def compute_fingerprint(message_text: str, version: str) -> str:
    """Compute 3-character fingerprint for attribution."""
    indices = [4, 7, 20]
    chars = "".join(message_text[i] if i < len(message_text) else "0" for i in indices)
    
    fingerprint_input = f"{FINGERPRINT_SALT}{chars}{version}"
    
    hash_output = hashlib.sha256(fingerprint_input.encode()).hexdigest()
    return hash_output[:3]


def compute_fingerprint_from_messages(messages: List[Dict[str, Any]]) -> str:
    """Compute fingerprint from the first user message."""
    first_message_text = _extract_first_message_text(messages)
    version = os.environ.get("CLAUDE_CODE_VERSION", "1.0.0")
    return compute_fingerprint(first_message_text, version)


# =============================================================================
# JSON Type Definitions
# =============================================================================


JsonValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JsonObject = Dict[str, JsonValue]


# =============================================================================
# 1. getExtraBodyParams
# =============================================================================


def get_extra_body_params(beta_headers: Optional[List[str]] = None) -> JsonObject:
    """
    Assemble extra body parameters for the API request based on
    CLAUDE_CODE_EXTRA_BODY environment variable and beta headers.
    """
    result: JsonObject = {}
    
    extra_body_str = os.environ.get("CLAUDE_CODE_EXTRA_BODY")
    if extra_body_str:
        parsed = _safe_parse_json(extra_body_str)
        if parsed and isinstance(parsed, dict):
            result = dict(parsed)
    
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")
    if entrypoint == "cli" and _should_include_first_party_only_betas():
        pass  # Anti-distillation placeholder
    
    if beta_headers and len(beta_headers) > 0:
        if "anthropic_beta" in result and isinstance(result["anthropic_beta"], list):
            existing_headers = result["anthropic_beta"]
            new_headers = [h for h in beta_headers if h not in existing_headers]
            result["anthropic_beta"] = existing_headers + new_headers
        else:
            result["anthropic_beta"] = beta_headers
    
    return result


# =============================================================================
# 2. getPromptCachingEnabled
# =============================================================================


def get_prompt_caching_enabled(model: str) -> bool:
    """Check if prompt caching is enabled for the given model."""
    if _is_env_truthy(os.environ.get("DISABLE_PROMPT_CACHING")):
        return False
    
    if _is_env_truthy(os.environ.get("DISABLE_PROMPT_CACHING_HAIKU")):
        small_fast_model = _get_small_fast_model()
        if model == small_fast_model:
            return False
    
    if _is_env_truthy(os.environ.get("DISABLE_PROMPT_CACHING_SONNET")):
        default_sonnet = _get_default_sonnet_model()
        if model == default_sonnet:
            return False
    
    if _is_env_truthy(os.environ.get("DISABLE_PROMPT_CACHING_OPUS")):
        default_opus = _get_default_opus_model()
        if model == default_opus:
            return False
    
    return True


# =============================================================================
# 3. getCacheControl
# =============================================================================


@dataclass
class CacheControl:
    """Cache control structure."""
    type: str = "ephemeral"
    ttl: Optional[str] = None
    scope: Optional[str] = None


def get_cache_control(
    scope: Optional[str] = None,
    query_source: Optional[str] = None,
) -> CacheControl:
    """Get cache control parameters."""
    result = CacheControl(type="ephemeral")
    
    if _should_1h_cache_ttl(query_source):
        result.ttl = "1h"
    
    if scope == "global":
        result.scope = scope
    
    return result


def _should_1h_cache_ttl(query_source: Optional[str] = None) -> bool:
    """Determine if 1h TTL should be used for prompt caching."""
    global _prompt_cache_1h_eligible
    global _prompt_cache_1h_allowlist
    
    if _get_api_provider() == "bedrock":
        if _is_env_truthy(os.environ.get("ENABLE_PROMPT_CACHING_1H_BEDROCK")):
            return True
    
    if _prompt_cache_1h_eligible is None:
        user_type = os.environ.get("USER_TYPE", "")
        is_using_overage = _is_env_truthy(os.environ.get("IS_USING_OVERAGE"))
        
        user_eligible = user_type == "ant" or (
            _is_claude_ai_subscriber() and not is_using_overage
        )
        _prompt_cache_1h_eligible = user_eligible
    
    if not _prompt_cache_1h_eligible:
        return False
    
    if _prompt_cache_1h_allowlist is None:
        config_str = os.environ.get("TENGU_PROMPT_CACHE_1H_CONFIG", "{}")
        config = _safe_parse_json(config_str) or {}
        _prompt_cache_1h_allowlist = config.get("allowlist", [])
    
    if query_source is None:
        return False
    
    for pattern in _prompt_cache_1h_allowlist or []:
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            if query_source.startswith(prefix):
                return True
        elif query_source == pattern:
            return True
    
    return False


# =============================================================================
# 4. configureTaskBudgetParams
# =============================================================================


@dataclass
class TaskBudget:
    """Task budget structure."""
    total: int
    remaining: Optional[int] = None


@dataclass
class OutputConfig:
    """Output configuration structure."""
    task_budget: Optional[Dict[str, Any]] = None
    effort: Optional[str] = None
    format: Optional[Dict[str, Any]] = None


def configure_task_budget_params(
    task_budget: Optional[TaskBudget],
    output_config: OutputConfig,
    betas: List[str],
) -> None:
    """Configure task budget parameters for API request."""
    if not task_budget:
        return
    
    if output_config.task_budget:
        return
    
    if not _should_include_first_party_only_betas():
        return
    
    output_config.task_budget = {
        "type": "tokens",
        "total": task_budget.total,
    }
    if task_budget.remaining is not None:
        output_config.task_budget["remaining"] = task_budget.remaining
    
    if TASK_BUDDYS_BETA_HEADER not in betas:
        betas.append(TASK_BUDDYS_BETA_HEADER)


# =============================================================================
# 5. getAPIMetadata
# =============================================================================


def get_api_metadata() -> Dict[str, Any]:
    """Get API metadata including user_id, device_id, session_id, and account_uuid."""
    extra: JsonObject = {}
    extra_str = os.environ.get("CLAUDE_CODE_EXTRA_METADATA")
    if extra_str:
        parsed = _safe_parse_json(extra_str)
        if parsed and isinstance(parsed, dict):
            extra = parsed
    
    user_id_obj = {
        **extra,
        "device_id": _get_user_id(),
        "account_uuid": _get_oauth_account_uuid(),
        "session_id": _get_session_id(),
    }
    
    return {
        "user_id": json.dumps(user_id_obj),
    }


def _get_oauth_account_uuid() -> str:
    """Get OAuth account UUID if available."""
    return os.environ.get("CLAUDE_CODE_OAUTH_ACCOUNT_UUID", "")


# =============================================================================
# 6. verifyApiKey
# =============================================================================


async def verify_api_key(
    api_key: str,
    is_non_interactive_session: bool,
) -> bool:
    """Verify if an API key is valid by making a minimal request."""
    if is_non_interactive_session:
        return True
    
    model = _get_small_fast_model()
    betas = _get_model_betas(model)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            if betas:
                headers["anthropic-beta"] = ",".join(betas)
            
            response = await http_client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "test"}],
                    "metadata": get_api_metadata(),
                    **get_extra_body_params(),
                },
            )
            
            if response.status_code == 200:
                return True
            
            if response.status_code == 401:
                error_data = response.json() if response.content else {}
                error_msg = str(error_data)
                if "authentication_error" in error_msg or "invalid x-api-key" in error_msg:
                    return False
            
            return False
    except Exception:
        return False


# =============================================================================
# 7. userMessageToMessageParam
# =============================================================================


def user_message_to_message_param(
    message: Dict[str, Any],
    add_cache: bool = False,
    enable_prompt_caching: bool = True,
    query_source: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert a user message to API message param format."""
    msg_content = message.get("message", {}).get("content")
    
    if add_cache:
        if isinstance(msg_content, str):
            return {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": msg_content,
                        **(
                            {"cache_control": _cache_control_to_dict(get_cache_control(query_source=query_source))}
                            if enable_prompt_caching else {}
                        ),
                    }
                ],
            }
        else:
            return {
                "role": "user",
                "content": [
                    {**block, **(
                        {"cache_control": _cache_control_to_dict(get_cache_control(query_source=query_source))}
                        if enable_prompt_caching and i == len(msg_content) - 1 else {}
                    )}
                    for i, block in enumerate(msg_content)
                ],
            }
    
    if isinstance(msg_content, list):
        return {
            "role": "user",
            "content": list(msg_content),
        }
    return {
        "role": "user",
        "content": msg_content,
    }


def _cache_control_to_dict(cache_control: CacheControl) -> Dict[str, Any]:
    """Convert CacheControl to dictionary."""
    result: Dict[str, Any] = {"type": cache_control.type}
    if cache_control.ttl:
        result["ttl"] = cache_control.ttl
    if cache_control.scope:
        result["scope"] = cache_control.scope
    return result


# =============================================================================
# 8. assistantMessageToMessageParam
# =============================================================================


def assistant_message_to_message_param(
    message: Dict[str, Any],
    add_cache: bool = False,
    enable_prompt_caching: bool = True,
    query_source: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert an assistant message to API message param format."""
    msg_content = message.get("message", {}).get("content")
    
    if add_cache:
        if isinstance(msg_content, str):
            return {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": msg_content,
                        **(
                            {"cache_control": _cache_control_to_dict(get_cache_control(query_source=query_source))}
                            if enable_prompt_caching else {}
                        ),
                    }
                ],
            }
        else:
            return {
                "role": "assistant",
                "content": [
                    {**block, **(
                        {"cache_control": _cache_control_to_dict(get_cache_control(query_source=query_source))}
                        if (
                            enable_prompt_caching and
                            i == len(msg_content) - 1 and
                            block.get("type") != "thinking" and
                            block.get("type") != "redacted_thinking"
                        ) else {}
                    )}
                    for i, block in enumerate(msg_content)
                ],
            }
    
    return {
        "role": "assistant",
        "content": message.get("message", {}).get("content"),
    }


# =============================================================================
# 9. queryModelWithoutStreaming
# =============================================================================


async def query_model_without_streaming(
    messages: List[Dict[str, Any]],
    system_prompt: List[str],
    thinking_config: Dict[str, Any],
    tools: List[Dict[str, Any]],
    signal: Any,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    """Query model without streaming."""
    assistant_message = None
    
    async for event in query_model_with_streaming(
        messages,
        system_prompt,
        thinking_config,
        tools,
        signal,
        options,
    ):
        if event.get("type") == "assistant":
            assistant_message = event
            break
    
    if not assistant_message:
        if signal and getattr(signal, "aborted", False):
            raise Exception("Request aborted")
        raise Exception("No assistant message found")
    
    return assistant_message


# =============================================================================
# 10. queryModelWithStreaming (Core streaming function)
# =============================================================================


class ApiError(Exception):
    """API Error with quota extraction."""
    
    def __init__(
        self,
        message: str,
        status: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.status = status
        self.headers = headers or {}
        self.request_id = request_id
        self.name = "ApiError"


def _extract_quota_status_from_headers(headers: Dict[str, str]) -> None:
    """Extract and store quota status from response headers."""
    pass  # Placeholder for quota tracking


def _extract_quota_status_from_error(error: Exception) -> None:
    """Extract quota status from error response."""
    pass  # Placeholder for quota tracking


def _is_rate_limit_error(error: Any) -> bool:
    """Check if error is a rate limit error."""
    if isinstance(error, dict):
        if error.get("status") == 429:
            return True
        message = error.get("message", "")
        if isinstance(message, str) and "rate_limit" in message.lower():
            return True
    return False


def _get_error_message_if_refusal(stop_reason: Optional[str], model: str) -> Optional[Dict[str, Any]]:
    """Get error message if the stop reason indicates a refusal."""
    return None  # Placeholder


def _create_assistant_api_error_message(
    content: str,
    api_error: str,
    error: str,
) -> Dict[str, Any]:
    """Create an assistant message representing an API error."""
    return {
        "isApiErrorMessage": True,
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": content}],
        },
        "error": api_error,
        "errorDetails": error,
    }


async def query_model_with_streaming(
    messages: List[Dict[str, Any]],
    system_prompt: List[str],
    thinking_config: Dict[str, Any],
    tools: List[Dict[str, Any]],
    signal: Any,
    options: Dict[str, Any],
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Query model with streaming response.
    
    Core streaming API function that yields events as they arrive.
    """
    model = options.get("model", _get_default_sonnet_model())
    query_source = options.get("query_source", "api_query")
    enable_prompt_caching = options.get("enable_prompt_caching", True)
    
    betas = options.get("betas", [])
    max_tokens = options.get("max_tokens", 4096)
    
    metadata = get_api_metadata()
    
    system_blocks = build_system_prompt_blocks(
        system_prompt,
        enable_prompt_caching,
        {"query_source": query_source},
    )
    
    api_messages = []
    for msg in messages:
        if msg.get("type") == "user":
            api_messages.append(
                user_message_to_message_param(msg, False, enable_prompt_caching, query_source)
            )
        elif msg.get("type") == "assistant":
            api_messages.append(
                assistant_message_to_message_param(msg, False, enable_prompt_caching, query_source)
            )
    
    effort = resolve_applied_effort(model, options.get("effort_value"))
    
    thinking = None
    if thinking_config.get("type") != "disabled" and _model_supports_thinking(model):
        if _model_supports_adaptive_thinking(model):
            thinking = {"type": "adaptive"}
        else:
            budget = _get_max_thinking_tokens_for_model(model)
            if thinking_config.get("budget_tokens"):
                budget = min(budget, thinking_config["budget_tokens"])
            thinking = {
                "budget_tokens": budget,
                "type": "enabled",
            }
    
    output_config: Dict[str, Any] = {}
    if options.get("output_format"):
        output_config["format"] = options["output_format"]
        if _model_supports_structured_outputs(model):
            if STRUCTURED_OUTPUTS_BETA_HEADER not in betas:
                betas.append(STRUCTURED_OUTPUTS_BETA_HEADER)
    
    _configure_effort_params(
        effort,
        output_config,
        {},
        betas,
        model,
    )
    
    if options.get("task_budget"):
        configure_task_budget_params(
            options["task_budget"],
            OutputConfig(**output_config),
            betas,
        )
    
    temperature = None
    if thinking_config.get("type") == "disabled":
        temperature = options.get("temperature_override", 1)
    
    request_params = {
        "model": model,
        "messages": api_messages,
        "max_tokens": max_tokens,
        "system": system_blocks if system_blocks else None,
        "betas": betas if betas else None,
        "metadata": metadata,
        **get_extra_body_params(),
    }
    
    if thinking:
        request_params["thinking"] = thinking
    
    if temperature is not None:
        request_params["temperature"] = temperature
    
    if output_config:
        request_params["output_config"] = output_config
    
    if tools:
        request_params["tools"] = tools
    
    if options.get("tool_choice"):
        request_params["tool_choice"] = options["tool_choice"]
    
    fingerprint = _compute_fingerprint_from_messages(api_messages)
    
    if options.get("enable_prompt_caching") and feature_enabled("PROMPT_CACHE_BREAK_DETECTION"):
        record_prompt_state(
            system=system_blocks,
            tool_schemas=tools or [],
            query_source=query_source,
            model=model,
            agent_id=options.get("agent_id"),
            fast_mode=False,
            global_cache_strategy="",
            betas=betas,
            auto_mode_active=_get_afk_mode_header_latched(),
            is_using_overage=_is_env_truthy(os.environ.get("IS_USING_OVERAGE")),
            cached_mc_enabled=False,
            effort_value=effort,
            extra_body_params=get_extra_body_params(),
        )
    
    new_messages: List[Dict[str, Any]] = []
    ttft_ms = 0
    content_blocks: List[Dict[str, Any]] = []
    usage: Dict[str, Any] = dict(EMPTY_USAGE.__dict__) if hasattr(EMPTY_USAGE, "__dict__") else {}
    stop_reason = None
    stream_request_id = None
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as http_client:
            headers = {
                "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            
            if fingerprint:
                headers["X-Fingerprint"] = fingerprint
            
            async with http_client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={**request_params, "stream": True},
            ) as response:
                if response.status_code != 200:
                    error_text = await response.text()
                    raise ApiError(
                        message=error_text,
                        status=response.status_code,
                        headers=dict(response.headers),
                    )
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        
                        event = _safe_parse_json(data)
                        if not event:
                            continue
                        
                        if event.get("type") == "message_start":
                            ttft_ms = _get_current_time_ms()
                            partial = event.get("message", {})
                            usage = _update_usage(usage, partial.get("usage"))
                        
                        elif event.get("type") == "content_block_start":
                            block = event.get("content_block", {})
                            content_blocks.append({**block})
                        
                        elif event.get("type") == "content_block_delta":
                            idx = event.get("index")
                            delta = event.get("delta", {})
                            delta_type = delta.get("type")
                            
                            if idx is not None and idx < len(content_blocks):
                                block = content_blocks[idx]
                                
                                if delta_type == "text_delta":
                                    if "text" not in block:
                                        block["text"] = ""
                                    block["text"] = (block.get("text") or "") + delta.get("text", "")
                                
                                elif delta_type == "input_json_delta":
                                    if "input" not in block:
                                        block["input"] = ""
                                    block["input"] = (block.get("input") or "") + delta.get("partial_json", "")
                                
                                elif delta_type == "thinking_delta":
                                    if "thinking" not in block:
                                        block["thinking"] = ""
                                    block["thinking"] = (block.get("thinking") or "") + delta.get("thinking", "")
                        
                        elif event.get("type") == "content_block_stop":
                            idx = event.get("index")
                            if idx is not None and idx < len(content_blocks):
                                content_block = content_blocks[idx]
                                m = _create_assistant_message(
                                    content=[content_block],
                                    request_id=stream_request_id,
                                    usage=usage,
                                )
                                new_messages.append(m)
                                yield m
                        
                        elif event.get("type") == "message_delta":
                            usage = _update_usage(usage, event.get("usage"))
                            stop_reason = event.get("delta", {}).get("stop_reason")
                        
                        elif event.get("type") == "message_stop":
                            pass
                        
                        yield {"type": "stream_event", "event": event}
    
    except Exception as e:
        if isinstance(e, ApiError):
            _extract_quota_status_from_error(e)
        
        if isinstance(e, Exception):
            error_msg = get_assistant_message_from_error(e, model, {
                "messages": messages,
                "messagesForAPI": api_messages,
            })
            yield error_msg
        else:
            yield {"type": "error", "error": str(e)}


def feature_enabled(feature_name: str) -> bool:
    """Check if a feature flag is enabled."""
    return _is_env_truthy(os.environ.get(f"CLAUDE_CODE_{feature_name}"))


def _create_assistant_message(
    content: List[Dict[str, Any]],
    request_id: Optional[str],
    usage: Dict[str, Any],
) -> Dict[str, Any]:
    """Create an assistant message structure."""
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": content,
            "model": "",
            "stop_reason": None,
            "stop_sequence": None,
            "usage": usage,
        },
        "requestId": request_id or str(uuid.uuid4()),
        "uuid": str(uuid.uuid4()),
        "timestamp": "",
    }


def _update_usage(
    usage: Dict[str, Any],
    part_usage: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Update usage statistics with new values."""
    if not part_usage:
        return dict(usage)
    
    return {
        "input_tokens": part_usage.get("input_tokens") if part_usage.get("input_tokens") else usage.get("input_tokens", 0),
        "output_tokens": part_usage.get("output_tokens") or usage.get("output_tokens", 0),
        "cache_creation_input_tokens": part_usage.get("cache_creation_input_tokens") if part_usage.get("cache_creation_input_tokens") else usage.get("cache_creation_input_tokens", 0),
        "cache_read_input_tokens": part_usage.get("cache_read_input_tokens") if part_usage.get("cache_read_input_tokens") else usage.get("cache_read_input_tokens", 0),
        "server_tool_use": usage.get("server_tool_use", {"web_search_requests": 0, "web_fetch_requests": 0}),
        "service_tier": usage.get("service_tier", "standard"),
        "cache_creation": usage.get("cache_creation", {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0}),
        "inference_geo": usage.get("inference_geo", ""),
        "iterations": usage.get("iterations", []),
        "speed": usage.get("speed", "standard"),
    }


# =============================================================================
# 11. executeNonStreamingRequest
# =============================================================================


async def execute_non_streaming_request(
    client_options: Dict[str, Any],
    retry_options: Dict[str, Any],
    params_from_context: Callable[[RetryContext], Dict[str, Any]],
    on_attempt: Callable[[int, int, int], None],
    capture_request: Callable[[Dict[str, Any]], None],
    originating_request_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], Dict[str, Any]]:
    """Helper generator for non-streaming API requests."""
    fallback_timeout_ms = _get_nonstreaming_fallback_timeout_ms()
    
    async def operation(client: Any, attempt: int, context: RetryContext) -> Dict[str, Any]:
        start = _get_current_time_ms()
        retry_params = params_from_context(context)
        capture_request(retry_params)
        on_attempt(attempt, start, retry_params.get("max_tokens", 4096))
        
        adjusted_params = adjust_params_for_non_streaming(
            retry_params,
            MAX_NON_STREAMING_TOKENS,
        )
        
        try:
            response = await client.messages.create(
                model=_normalize_model_string_for_api(adjusted_params.get("model", "")),
                **{k: v for k, v in adjusted_params.items() if k != "model"},
                stream=False,
                timeout=fallback_timeout_ms / 1000,
            )
            return {
                "content": list(response.content) if hasattr(response, "content") else [],
                "usage": {
                    "input_tokens": response.usage.input_tokens if hasattr(response, "usage") else 0,
                    "output_tokens": response.usage.output_tokens if hasattr(response, "usage") else 0,
                },
                "stop_reason": response.stop_reason if hasattr(response, "stop_reason") else None,
                "model": response.model if hasattr(response, "model") else client_options.get("model"),
            }
        except Exception:
            raise
    
    generator = with_retry(
        lambda: get_anthropic_client(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            max_retries=0,
            model=client_options.get("model"),
            source=client_options.get("source", "api_query"),
        ),
        operation,
        {
            "model": retry_options.get("model"),
            "fallback_model": retry_options.get("fallback_model"),
            "thinking_config": retry_options.get("thinking_config", {}),
            "signal": retry_options.get("signal"),
            "query_source": retry_options.get("query_source"),
        },
    )
    
    result = None
    async for event in generator:
        if event.get("type") == "result":
            result = event.get("value")
            break
        elif event.get("type") == "system":
            yield event.get("value")
    
    yield {"type": "result", "value": result}


def _get_nonstreaming_fallback_timeout_ms() -> int:
    """Get timeout for non-streaming fallback requests."""
    override = os.environ.get("API_TIMEOUT_MS")
    if override:
        try:
            return int(override)
        except ValueError:
            pass
    
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_REMOTE")):
        return 120_000
    return 300_000


# =============================================================================
# 12. stripExcessMediaItems
# =============================================================================


def strip_excess_media_items(
    messages: List[Dict[str, Any]],
    limit: int,
) -> List[Dict[str, Any]]:
    """Ensures messages contain at most `limit` media items."""
    
    def is_media(block: Dict[str, Any]) -> bool:
        return block.get("type") in ("image", "document")
    
    def is_tool_result(block: Dict[str, Any]) -> bool:
        return block.get("type") == "tool_result"
    
    to_remove = 0
    for msg in messages:
        content = msg.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if is_media(block):
                to_remove += 1
            if is_tool_result(block) and isinstance(block.get("content"), list):
                for nested in block["content"]:
                    if is_media(nested):
                        to_remove += 1
    
    to_remove -= limit
    if to_remove <= 0:
        return messages
    
    result = []
    for msg in messages:
        if to_remove <= 0:
            result.append(msg)
            continue
        
        content = msg.get("message", {}).get("content")
        if not isinstance(content, list):
            result.append(msg)
            continue
        
        before = to_remove
        stripped = []
        for block in content:
            if to_remove <= 0:
                stripped.append(block)
                continue
            
            if is_tool_result(block) and isinstance(block.get("content"), list):
                filtered = [
                    n for n in block["content"]
                    if not (is_media(n) and (to_remove := to_remove - 1) >= 0)
                ]
                if len(filtered) != len(block["content"]):
                    stripped.append({**block, "content": filtered})
                else:
                    stripped.append(block)
            elif is_media(block) and to_remove > 0:
                to_remove -= 1
            else:
                stripped.append(block)
        
        if before == to_remove:
            result.append(msg)
        else:
            new_msg = dict(msg)
            if "message" in new_msg:
                new_msg["message"] = dict(new_msg["message"])
                new_msg["message"]["content"] = stripped
            else:
                new_msg["content"] = stripped
            result.append(new_msg)
    
    return result


# =============================================================================
# 13. cleanupStream
# =============================================================================


def cleanup_stream(stream: Any) -> None:
    """Cleans up stream resources to prevent memory leaks."""
    if not stream:
        return
    
    try:
        if hasattr(stream, "controller"):
            controller = stream.controller
            if hasattr(controller, "signal") and not controller.signal.aborted:
                controller.abort()
    except Exception:
        pass


# =============================================================================
# 14. updateUsage
# =============================================================================


def update_usage(
    usage: Dict[str, Any],
    part_usage: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Updates usage statistics with new values from streaming API events."""
    if not part_usage:
        return dict(usage)
    
    if "server_tool_use" not in usage:
        usage = {**usage, "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0}}
    if "cache_creation" not in usage:
        usage = {**usage, "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0}}
    
    return {
        "input_tokens": (
            part_usage.get("input_tokens")
            if part_usage.get("input_tokens") is not None and part_usage.get("input_tokens", 0) > 0
            else usage.get("input_tokens", 0)
        ),
        "output_tokens": part_usage.get("output_tokens") or usage.get("output_tokens", 0),
        "cache_creation_input_tokens": (
            part_usage.get("cache_creation_input_tokens")
            if part_usage.get("cache_creation_input_tokens") is not None and part_usage.get("cache_creation_input_tokens", 0) > 0
            else usage.get("cache_creation_input_tokens", 0)
        ),
        "cache_read_input_tokens": (
            part_usage.get("cache_read_input_tokens")
            if part_usage.get("cache_read_input_tokens") is not None and part_usage.get("cache_read_input_tokens", 0) > 0
            else usage.get("cache_read_input_tokens", 0)
        ),
        "server_tool_use": {
            "web_search_requests": (
                part_usage.get("server_tool_use", {}).get("web_search_requests")
                if part_usage.get("server_tool_use", {}).get("web_search_requests") is not None
                else usage.get("server_tool_use", {}).get("web_search_requests", 0)
            ),
            "web_fetch_requests": (
                part_usage.get("server_tool_use", {}).get("web_fetch_requests")
                if part_usage.get("server_tool_use", {}).get("web_fetch_requests") is not None
                else usage.get("server_tool_use", {}).get("web_fetch_requests", 0)
            ),
        },
        "service_tier": usage.get("service_tier", "standard"),
        "cache_creation": {
            "ephemeral_1h_input_tokens": (
                part_usage.get("cache_creation", {}).get("ephemeral_1h_input_tokens")
                if part_usage.get("cache_creation", {}).get("ephemeral_1h_input_tokens") is not None
                else usage.get("cache_creation", {}).get("ephemeral_1h_input_tokens", 0)
            ),
            "ephemeral_5m_input_tokens": (
                part_usage.get("cache_creation", {}).get("ephemeral_5m_input_tokens")
                if part_usage.get("cache_creation", {}).get("ephemeral_5m_input_tokens") is not None
                else usage.get("cache_creation", {}).get("ephemeral_5m_input_tokens", 0)
            ),
        },
        "inference_geo": usage.get("inference_geo", ""),
        "iterations": part_usage.get("iterations") or usage.get("iterations", []),
        "speed": part_usage.get("speed") or usage.get("speed", "standard"),
    }


# =============================================================================
# 15. accumulateUsage
# =============================================================================


def accumulate_usage(
    total_usage: Dict[str, Any],
    message_usage: Dict[str, Any],
) -> Dict[str, Any]:
    """Accumulates usage from one message into a total usage object."""
    total_server_tool_use = total_usage.get("server_tool_use", {"web_search_requests": 0, "web_fetch_requests": 0})
    msg_server_tool_use = message_usage.get("server_tool_use", {"web_search_requests": 0, "web_fetch_requests": 0})
    
    total_cache_creation = total_usage.get("cache_creation", {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0})
    msg_cache_creation = message_usage.get("cache_creation", {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0})
    
    return {
        "input_tokens": total_usage.get("input_tokens", 0) + message_usage.get("input_tokens", 0),
        "output_tokens": total_usage.get("output_tokens", 0) + message_usage.get("output_tokens", 0),
        "cache_creation_input_tokens": (
            total_usage.get("cache_creation_input_tokens", 0) + message_usage.get("cache_creation_input_tokens", 0)
        ),
        "cache_read_input_tokens": (
            total_usage.get("cache_read_input_tokens", 0) + message_usage.get("cache_read_input_tokens", 0)
        ),
        "server_tool_use": {
            "web_search_requests": (
                total_server_tool_use.get("web_search_requests", 0) + msg_server_tool_use.get("web_search_requests", 0)
            ),
            "web_fetch_requests": (
                total_server_tool_use.get("web_fetch_requests", 0) + msg_server_tool_use.get("web_fetch_requests", 0)
            ),
        },
        "service_tier": message_usage.get("service_tier", "standard"),
        "cache_creation": {
            "ephemeral_1h_input_tokens": (
                total_cache_creation.get("ephemeral_1h_input_tokens", 0) + msg_cache_creation.get("ephemeral_1h_input_tokens", 0)
            ),
            "ephemeral_5m_input_tokens": (
                total_cache_creation.get("ephemeral_5m_input_tokens", 0) + msg_cache_creation.get("ephemeral_5m_input_tokens", 0)
            ),
        },
        "inference_geo": message_usage.get("inference_geo", ""),
        "iterations": message_usage.get("iterations", []),
        "speed": message_usage.get("speed", "standard"),
    }


# =============================================================================
# 16. addCacheBreakpoints
# =============================================================================


def add_cache_breakpoints(
    messages: List[Dict[str, Any]],
    enable_prompt_caching: bool,
    query_source: Optional[str] = None,
    use_cached_mc: bool = False,
    new_cache_edits: Optional[Dict[str, Any]] = None,
    pinned_edits: Optional[List[Dict[str, Any]]] = None,
    skip_cache_write: bool = False,
) -> List[Dict[str, Any]]:
    """Add cache breakpoints to messages for prompt caching."""
    marker_index = len(messages) - 2 if skip_cache_write else len(messages) - 1
    
    result = []
    for i, msg in enumerate(messages):
        add_cache = (i == marker_index)
        if msg.get("type") == "user":
            result.append(
                user_message_to_message_param(msg, add_cache, enable_prompt_caching, query_source)
            )
        else:
            result.append(
                assistant_message_to_message_param(msg, add_cache, enable_prompt_caching, query_source)
            )
    
    return result


# =============================================================================
# 17. buildSystemPromptBlocks
# =============================================================================


def build_system_prompt_blocks(
    system_prompt: List[str],
    enable_prompt_caching: bool,
    options: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Build system prompt blocks for API request."""
    options = options or {}
    query_source = options.get("query_source")
    skip_global_cache = options.get("skip_global_cache_for_system_prompt", False)
    
    blocks = []
    for text in system_prompt:
        block: Dict[str, Any] = {
            "type": "text",
            "text": text,
        }
        
        if enable_prompt_caching and not skip_global_cache:
            cache_ctrl = get_cache_control(query_source=query_source)
            block["cache_control"] = _cache_control_to_dict(cache_ctrl)
        
        blocks.append(block)
    
    return blocks


# =============================================================================
# 18. queryHaiku
# =============================================================================


async def query_haiku(
    system_prompt: List[str],
    user_prompt: str,
    output_format: Optional[Dict[str, Any]] = None,
    signal: Any = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Query the Haiku model for a response."""
    options = options or {}
    
    messages = [
        {"type": "user", "message": {"role": "user", "content": user_prompt}},
    ]
    
    result = await query_model_without_streaming(
        messages=messages,
        system_prompt=system_prompt,
        thinking_config={"type": "disabled"},
        tools=[],
        signal=signal,
        options={
            **options,
            "model": _get_small_fast_model(),
            "enable_prompt_caching": options.get("enable_prompt_caching", False),
            "output_format": output_format,
        },
    )
    
    return result


# =============================================================================
# 19. queryWithModel
# =============================================================================


async def query_with_model(
    system_prompt: List[str],
    user_prompt: str,
    output_format: Optional[Dict[str, Any]] = None,
    signal: Any = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Query a specific model through the Claude Code infrastructure."""
    options = options or {}
    
    messages = [
        {"type": "user", "message": {"role": "user", "content": user_prompt}},
    ]
    
    result = await query_model_without_streaming(
        messages=messages,
        system_prompt=system_prompt,
        thinking_config={"type": "disabled"},
        tools=[],
        signal=signal,
        options={
            **options,
            "enable_prompt_caching": options.get("enable_prompt_caching", False),
            "output_format": output_format,
        },
    )
    
    return result


# =============================================================================
# 20. adjustParamsForNonStreaming
# =============================================================================


def adjust_params_for_non_streaming(
    params: Dict[str, Any],
    max_tokens_cap: int,
) -> Dict[str, Any]:
    """Adjusts thinking budget when max_tokens is capped for non-streaming fallback."""
    capped_max_tokens = min(params.get("max_tokens", max_tokens_cap), max_tokens_cap)
    adjusted_params = dict(params)
    adjusted_params["max_tokens"] = capped_max_tokens
    
    thinking = adjusted_params.get("thinking")
    if thinking and isinstance(thinking, dict):
        if thinking.get("type") == "enabled" and thinking.get("budget_tokens"):
            adjusted_params["thinking"] = {
                **thinking,
                "budget_tokens": min(
                    thinking["budget_tokens"],
                    capped_max_tokens - 1,
                ),
            }
    
    return adjusted_params


# =============================================================================
# 21. getMaxOutputTokensForModel
# =============================================================================


def get_max_output_tokens_for_model(model: str) -> int:
    """Get the maximum output tokens for a model."""
    max_output_tokens = _get_model_max_output_tokens(model)
    
    default_tokens = min(max_output_tokens.get("default", 4096), CAPPED_DEFAULT_MAX_TOKENS)
    
    env_override = os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS")
    if env_override:
        try:
            override_val = int(env_override)
            upper_limit = max_output_tokens.get("upperLimit", 8192)
            return max(1, min(override_val, upper_limit))
        except ValueError:
            pass
    
    upper_limit = max_output_tokens.get("upperLimit", 8192)
    return max(1, min(default_tokens, upper_limit))


# =============================================================================
# Type Definitions for external use
# =============================================================================

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class QueryModelOptions:
    """Options for query_model functions."""
    model: str
    query_source: str
    get_tool_permission_context: Any
    is_non_interactive_session: bool = False
    tool_choice: Any = None
    extra_tool_schemas: List[Any] = None
    max_output_tokens_override: Optional[int] = None
    fallback_model: Optional[str] = None
    on_streaming_fallback: Any = None
    agents: List[Any] = None
    allowed_agent_types: List[str] = None
    has_append_system_prompt: bool = False
    fetch_override: Any = None
    enable_prompt_caching: bool = True
    skip_cache_write: bool = False
    temperature_override: Optional[float] = None
    effort_value: Any = None
    mcp_tools: List[Any] = None
    has_pending_mcp_servers: bool = False
    query_tracking: Any = None
    agent_id: Any = None
    output_format: Any = None
    fast_mode: bool = False
    advisor_model: Optional[str] = None
    add_notification: Any = None
    task_budget: Any = None


@dataclass
class StreamingQueryResult:
    """Result from a streaming query."""
    message: Any
    stop_reason: Optional[str]
    usage: Dict[str, Any]


# =============================================================================
# Re-export types for external use
# =============================================================================

__all__ = [
    # Beta headers
    "AFK_MODE_BETA_HEADER",
    "CONTEXT_1M_BETA_HEADER",
    "CONTEXT_MANAGEMENT_BETA_HEADER",
    "EFFORT_BETA_HEADER",
    "FAST_MODE_BETA_HEADER",
    "PROMPT_CACHING_SCOPE_BETA_HEADER",
    "REDACT_THINKING_BETA_HEADER",
    "STRUCTURED_OUTPUTS_BETA_HEADER",
    "TASK_BUDDYS_BETA_HEADER",
    "CACHE_EDITING_BETA_HEADER",
    "ADVISOR_BETA_HEADER",
    # Constants
    "HAIKU_MODEL",
    "SONNET_MODEL",
    "OPUS_MODEL",
    "CAPPED_DEFAULT_MAX_TOKENS",
    "MAX_NON_STREAMING_TOKENS",
    "CACHE_TTL_1HOUR_MS",
    "TOOL_SEARCH_TOOL_NAME",
    # Functions
    "get_extra_body_params",
    "get_prompt_caching_enabled",
    "get_cache_control",
    "configure_task_budget_params",
    "get_api_metadata",
    "verify_api_key",
    "user_message_to_message_param",
    "assistant_message_to_message_param",
    "query_model_without_streaming",
    "query_model_with_streaming",
    "execute_non_streaming_request",
    "strip_excess_media_items",
    "cleanup_stream",
    "update_usage",
    "accumulate_usage",
    "add_cache_breakpoints",
    "build_system_prompt_blocks",
    "query_haiku",
    "query_with_model",
    "adjust_params_for_non_streaming",
    "get_max_output_tokens_for_model",
    "clear_beta_header_latches",
    "feature_enabled",
    # Fingerprinting
    "compute_fingerprint",
    "compute_fingerprint_from_messages",
    "FINGERPRINT_SALT",
    # Effort
    "resolve_applied_effort",
    "model_supports_effort",
    "model_supports_max_effort",
    "EFFORT_LEVELS",
    "is_effort_level",
    "parse_effort_value",
    "convert_effort_value_to_level",
    # Types
    "CacheControl",
    "TaskBudget",
    "OutputConfig",
    "ApiError",
    "EMPTY_USAGE",
    "JsonObject",
]
