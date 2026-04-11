from dataclasses import dataclass
from typing import Optional, Any, Dict
import os


@dataclass
class EMPTY_USAGE:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


GlobalCacheStrategy = str


def _is_env_truthy(env_var: Optional[str]) -> bool:
    if not env_var:
        return False
    return env_var.lower() in ("true", "1", "yes")


def _detect_gateway(headers: Optional[Dict[str, str]] = None, base_url: Optional[str] = None) -> Optional[str]:
    gateway_fingerprints = {
        "litellm": ["x-litellm-"],
        "helicone": ["helicone-"],
        "portkey": ["x-portkey-"],
        "cloudflare-ai-gateway": ["cf-aig-"],
        "kong": ["x-kong-"],
        "braintrust": ["x-bt-"],
    }
    
    if headers:
        for key in headers:
            for gateway, prefixes in gateway_fingerprints.items():
                if any(key.startswith(p) for p in prefixes):
                    return gateway
    
    if base_url:
        try:
            hostname = base_url.lower()
            if ".cloud.databricks.com" in hostname:
                return "databricks"
            if ".azuredatabricks.net" in hostname:
                return "databricks"
            if ".gcp.databricks.com" in hostname:
                return "databricks"
        except Exception:
            pass
    
    return None


def _get_error_message(error: Any) -> str:
    if isinstance(error, dict):
        error_body = error.get("error", {})
        if isinstance(error_body, dict):
            return error_body.get("message", str(error))
        return str(error)
    if hasattr(error, "message"):
        return str(error.message)
    return str(error)


def _get_anthropic_env_metadata() -> Dict[str, Any]:
    metadata = {}
    if os.environ.get("ANTHROPIC_BASE_URL"):
        metadata["baseUrl"] = os.environ["ANTHROPIC_BASE_URL"]
    if os.environ.get("ANTHROPIC_MODEL"):
        metadata["envModel"] = os.environ["ANTHROPIC_MODEL"]
    if os.environ.get("ANTHROPIC_SMALL_FAST_MODEL"):
        metadata["envSmallFastModel"] = os.environ["ANTHROPIC_SMALL_FAST_MODEL"]
    return metadata


def log_api_query(
    model: str,
    messages_length: int,
    temperature: float,
    query_source: str,
    betas: Optional[list[str]] = None,
    permission_mode: Optional[str] = None,
    query_tracking: Optional[Dict[str, Any]] = None,
    thinking_type: Optional[str] = None,
    effort_value: Optional[Any] = None,
    fast_mode: Optional[bool] = None,
    previous_request_id: Optional[str] = None,
) -> None:
    event = {
        "event": "tengu_api_query",
        "model": model,
        "messagesLength": messages_length,
        "temperature": temperature,
        "provider": _get_api_provider(),
        "querySource": query_source,
        "thinkingType": thinking_type,
        "effortValue": effort_value,
        "fastMode": fast_mode,
        "previousRequestId": previous_request_id,
        **_get_anthropic_env_metadata(),
    }
    
    if betas and len(betas) > 0:
        event["betas"] = ",".join(betas)
    if permission_mode:
        event["permissionMode"] = permission_mode
    if query_tracking:
        event["queryChainId"] = query_tracking.get("chainId")
        event["queryDepth"] = query_tracking.get("depth")


def log_api_error(
    error: Any,
    model: str,
    message_count: int,
    duration_ms: int,
    duration_ms_including_retries: int,
    attempt: int,
    request_id: Optional[str] = None,
    client_request_id: Optional[str] = None,
    did_fallback_to_non_streaming: Optional[bool] = None,
    prompt_category: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    query_tracking: Optional[Dict[str, Any]] = None,
    query_source: Optional[str] = None,
    llm_span: Optional[Any] = None,
    fast_mode: Optional[bool] = None,
    previous_request_id: Optional[str] = None,
    message_tokens: Optional[int] = None,
) -> None:
    gateway = _detect_gateway(
        headers=headers,
        base_url=os.environ.get("ANTHROPIC_BASE_URL"),
    )
    
    err_str = _get_error_message(error)
    status = None
    if isinstance(error, dict):
        status = str(error.get("status", ""))
    error_type = _classify_error(error)
    
    event = {
        "event": "tengu_api_error",
        "model": model,
        "error": err_str,
        "status": status,
        "errorType": error_type,
        "messageCount": message_count,
        "messageTokens": message_tokens,
        "durationMs": duration_ms,
        "durationMsIncludingRetries": duration_ms_including_retries,
        "attempt": attempt,
        "provider": _get_api_provider(),
        "requestId": request_id,
        "didFallBackToNonStreaming": did_fallback_to_non_streaming,
        "promptCategory": prompt_category,
        "gateway": gateway,
        "querySource": query_source,
        "fastMode": fast_mode,
        "previousRequestId": previous_request_id,
        **_get_anthropic_env_metadata(),
    }
    
    if client_request_id:
        event["clientRequestId"] = client_request_id
    if query_tracking:
        event["queryChainId"] = query_tracking.get("chainId")
        event["queryDepth"] = query_tracking.get("depth")


def log_api_success(
    model: str,
    pre_normalized_model: str,
    message_count: int,
    message_tokens: int,
    usage: Dict[str, int],
    duration_ms: int,
    duration_ms_including_retries: int,
    attempt: int,
    ttft_ms: Optional[float],
    request_id: Optional[str],
    stop_reason: Optional[str],
    cost_usd: float,
    did_fallback_to_non_streaming: bool,
    query_source: str,
    gateway: Optional[str] = None,
    query_tracking: Optional[Dict[str, Any]] = None,
    permission_mode: Optional[str] = None,
    global_cache_strategy: Optional[GlobalCacheStrategy] = None,
    text_content_length: Optional[int] = None,
    thinking_content_length: Optional[int] = None,
    tool_use_content_lengths: Optional[Dict[str, int]] = None,
    connector_text_block_count: Optional[int] = None,
    fast_mode: Optional[bool] = None,
    previous_request_id: Optional[str] = None,
    betas: Optional[list[str]] = None,
) -> None:
    pass


def _build_success_event(
    model: str,
    pre_normalized_model: str,
    message_count: int,
    message_tokens: int,
    usage: Dict[str, int],
    duration_ms: int,
    duration_ms_including_retries: int,
    attempt: int,
    ttft_ms: Optional[float],
    request_id: Optional[str],
    stop_reason: Optional[str],
    cost_usd: float,
    did_fallback_to_non_streaming: bool,
    query_source: str,
    gateway: Optional[str],
    query_tracking: Optional[Dict[str, Any]],
    permission_mode: Optional[str],
    global_cache_strategy: Optional[GlobalCacheStrategy],
    text_content_length: Optional[int],
    thinking_content_length: Optional[int],
    tool_use_content_lengths: Optional[Dict[str, int]],
    connector_text_block_count: Optional[int],
    fast_mode: Optional[bool],
    previous_request_id: Optional[str],
    betas: Optional[list[str]],
) -> Dict[str, Any]:
    return {
        "event": "tengu_api_success",
        "model": model,
        "preNormalizedModel": pre_normalized_model,
        "betas": ",".join(betas) if betas and len(betas) > 0 else None,
        "messageCount": message_count,
        "messageTokens": message_tokens,
        "inputTokens": usage.get("input_tokens", 0),
        "outputTokens": usage.get("output_tokens", 0),
        "cachedInputTokens": usage.get("cache_read_input_tokens", 0),
        "uncachedInputTokens": usage.get("cache_creation_input_tokens", 0),
        "durationMs": duration_ms,
        "durationMsIncludingRetries": duration_ms_including_retries,
        "attempt": attempt,
        "ttftMs": ttft_ms,
        "provider": _get_api_provider(),
        "requestId": request_id,
        "stopReason": stop_reason,
        "costUSD": cost_usd,
        "didFallBackToNonStreaming": did_fallback_to_non_streaming,
        "querySource": query_source,
        "gateway": gateway,
        "permissionMode": permission_mode,
        "globalCacheStrategy": global_cache_strategy,
        "textContentLength": text_content_length,
        "thinkingContentLength": thinking_content_length,
        "toolUseContentLengths": tool_use_content_lengths,
        "connectorTextBlockCount": connector_text_block_count,
        "fastMode": fast_mode,
        "previousRequestId": previous_request_id,
        **_get_anthropic_env_metadata(),
    }


def log_api_success_and_duration(
    model: str,
    pre_normalized_model: str,
    start: int,
    start_including_retries: int,
    ttft_ms: Optional[float],
    usage: Dict[str, int],
    attempt: int,
    message_count: int,
    message_tokens: int,
    request_id: Optional[str],
    stop_reason: Optional[str],
    did_fallback_to_non_streaming: bool,
    query_source: str,
    cost_usd: float,
    headers: Optional[Dict[str, str]] = None,
    query_tracking: Optional[Dict[str, Any]] = None,
    permission_mode: Optional[str] = None,
    new_messages: Optional[list[Dict[str, Any]]] = None,
    llm_span: Optional[Any] = None,
    global_cache_strategy: Optional[GlobalCacheStrategy] = None,
    request_setup_ms: Optional[int] = None,
    attempt_start_times: Optional[list[int]] = None,
    fast_mode: Optional[bool] = None,
    previous_request_id: Optional[str] = None,
    betas: Optional[list[str]] = None,
) -> None:
    gateway = _detect_gateway(
        headers=headers,
        base_url=os.environ.get("ANTHROPIC_BASE_URL"),
    )
    
    duration_ms = _get_current_time_ms() - start
    duration_ms_including_retries = _get_current_time_ms() - start_including_retries
    
    text_content_length = None
    thinking_content_length = None
    tool_use_content_lengths = None
    connector_text_block_count = None
    
    if new_messages:
        text_len = 0
        thinking_len = 0
        has_tool_use = False
        tool_lengths: Dict[str, int] = {}
        connector_count = 0
        
        for msg in new_messages:
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "text":
                        text_len += len(block.get("text", ""))
                    elif block.get("type") == "thinking":
                        thinking_len += len(block.get("thinking", ""))
                    elif block.get("type") in ("tool_use", "server_tool_use", "mcp_tool_use"):
                        tool_name = block.get("name", "unknown")
                        tool_input = block.get("input", {})
                        tool_lengths[tool_name] = tool_lengths.get(tool_name, 0) + len(str(tool_input))
                        has_tool_use = True
                    elif block.get("type") == "connector_text":
                        connector_count += 1
        
        text_content_length = text_len
        thinking_content_length = thinking_len if thinking_len > 0 else None
        tool_use_content_lengths = tool_lengths if has_tool_use else None
        connector_text_block_count = connector_count if connector_count > 0 else None
    
    log_api_success(
        model=model,
        pre_normalized_model=pre_normalized_model,
        message_count=message_count,
        message_tokens=message_tokens,
        usage=usage,
        duration_ms=duration_ms,
        duration_ms_including_retries=duration_ms_including_retries,
        attempt=attempt,
        ttft_ms=ttft_ms,
        request_id=request_id,
        stop_reason=stop_reason,
        cost_usd=cost_usd,
        did_fallback_to_non_streaming=did_fallback_to_non_streaming,
        query_source=query_source,
        gateway=gateway,
        query_tracking=query_tracking,
        permission_mode=permission_mode,
        global_cache_strategy=global_cache_strategy,
        text_content_length=text_content_length,
        thinking_content_length=thinking_content_length,
        tool_use_content_lengths=tool_use_content_lengths,
        connector_text_block_count=connector_text_block_count,
        fast_mode=fast_mode,
        previous_request_id=previous_request_id,
        betas=betas,
    )


def _get_api_provider() -> str:
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_BEDROCK")):
        return "bedrock"
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_FOUNDRY")):
        return "foundry"
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_VERTEX")):
        return "vertex"
    return "firstParty"


def _get_current_time_ms() -> int:
    import time
    return int(time.time() * 1000)


def _classify_error(error: Any) -> str:
    from .errors import classify_api_error
    return classify_api_error(error)
