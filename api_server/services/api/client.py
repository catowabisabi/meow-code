import os
from dataclasses import dataclass
from typing import Optional, Any, Callable


@dataclass
class ApiClientConfig:
    api_key: Optional[str] = None
    max_retries: int = 10
    model: Optional[str] = None
    base_url: Optional[str] = None
    auth_token: Optional[str] = None
    timeout_ms: int = 600000


def _is_env_truthy(env_var: Optional[str]) -> bool:
    if not env_var:
        return False
    return env_var.lower() in ("true", "1", "yes")


def _get_aws_region() -> str:
    return os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))


def _get_vertex_region_for_model(model: Optional[str]) -> str:
    if model:
        model_lower = model.lower()
        if "haiku" in model_lower:
            region = os.environ.get("VERTEX_REGION_CLAUDE_HAIKU_4_5")
            if not region:
                region = os.environ.get("VERTEX_REGION_CLAUDE_3_5_HAIKU")
        elif "sonnet" in model_lower:
            region = os.environ.get("VERTEX_REGION_CLAUDE_3_5_SONNET")
            if not region:
                region = os.environ.get("VERTEX_REGION_CLAUDE_3_7_SONNET")
        else:
            region = None
        if region:
            return region
    return os.environ.get("CLOUD_ML_REGION", "us-east5")


async def get_anthropic_client(
    api_key: Optional[str] = None,
    max_retries: int = 10,
    model: Optional[str] = None,
    fetch_override: Optional[Callable[..., Any]] = None,
) -> Any:
    """
    Get an Anthropic API client configured for the current environment.
    
    Supports multiple providers:
    - Direct API (default)
    - AWS Bedrock (via CLAUDE_CODE_USE_BEDROCK)
    - Microsoft Foundry (via CLAUDE_CODE_USE_FOUNDRY)
    - Google Vertex AI (via CLAUDE_CODE_USE_VERTEX)
    """
    container_id = os.environ.get("CLAUDE_CODE_CONTAINER_ID")
    remote_session_id = os.environ.get("CLAUDE_CODE_REMOTE_SESSION_ID")
    client_app = os.environ.get("CLAUDE_AGENT_SDK_CLIENT_APP")
    
    custom_headers = _get_custom_headers()
    default_headers = {
        "x-app": "cli",
        "x-claude-code-session-id": os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
        **custom_headers,
    }
    
    if container_id:
        default_headers["x-claude-remote-container-id"] = container_id
    if remote_session_id:
        default_headers["x-claude-remote-session-id"] = remote_session_id
    if client_app:
        default_headers["x-client-app"] = client_app
    
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_ADDITIONAL_PROTECTION")):
        default_headers["x-anthropic-additional-protection"] = "true"
    
    timeout_ms = int(os.environ.get("API_TIMEOUT_MS", "600000"))
    
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_BEDROCK")):
        return await _create_bedrock_client(
            default_headers=default_headers,
            max_retries=max_retries,
            timeout_ms=timeout_ms,
            model=model,
        )
    
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_FOUNDRY")):
        return await _create_foundry_client(
            default_headers=default_headers,
            max_retries=max_retries,
            timeout_ms=timeout_ms,
        )
    
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_VERTEX")):
        return await _create_vertex_client(
            default_headers=default_headers,
            max_retries=max_retries,
            timeout_ms=timeout_ms,
            model=model,
        )
    
    return _create_direct_client(
        api_key=api_key,
        default_headers=default_headers,
        max_retries=max_retries,
        timeout_ms=timeout_ms,
    )


async def _create_bedrock_client(
    default_headers: dict,
    max_retries: int,
    timeout_ms: int,
    model: Optional[str],
) -> Any:
    # Placeholder for Bedrock SDK integration
    # In production, this would use @anthropic-ai/bedrock-sdk
    # For now, return a mock/configured client
    aws_region = _get_aws_region()
    
    bedrock_args = {
        "aws_region": aws_region,
        "max_retries": max_retries,
        "timeout": timeout_ms,
    }
    
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        bedrock_args["skip_auth"] = True
        default_headers["Authorization"] = f"Bearer {os.environ['AWS_BEARER_TOKEN_BEDROCK']}"
    
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_SKIP_BEDROCK_AUTH")):
        bedrock_args["skip_auth"] = True
    
    return _MockAnthropicClient(
        provider="bedrock",
        region=aws_region,
        config=bedrock_args,
        headers=default_headers,
    )


async def _create_foundry_client(
    default_headers: dict,
    max_retries: int,
    timeout_ms: int,
) -> Any:
    # Placeholder for Foundry SDK integration
    # In production, this would use @anthropic-ai/foundry-sdk
    foundry_resource = os.environ.get("ANTHROPIC_FOUNDRY_RESOURCE", "")
    foundry_base_url = os.environ.get("ANTHROPIC_FOUNDRY_BASE_URL")
    
    if not foundry_base_url and foundry_resource:
        foundry_base_url = f"https://{foundry_resource}.services.ai.azure.com"
    
    foundry_args = {
        "max_retries": max_retries,
        "timeout": timeout_ms,
    }
    
    if foundry_base_url:
        foundry_args["base_url"] = foundry_base_url
    
    if os.environ.get("ANTHROPIC_FOUNDRY_API_KEY"):
        foundry_args["api_key"] = os.environ["ANTHROPIC_FOUNDRY_API_KEY"]
    
    return _MockAnthropicClient(
        provider="foundry",
        config=foundry_args,
        headers=default_headers,
    )


async def _create_vertex_client(
    default_headers: dict,
    max_retries: int,
    timeout_ms: int,
    model: Optional[str],
) -> Any:
    # Placeholder for Vertex SDK integration
    # In production, this would use @anthropic-ai/vertex-sdk
    region = _get_vertex_region_for_model(model)
    
    vertex_args = {
        "region": region,
        "max_retries": max_retries,
        "timeout": timeout_ms,
    }
    
    project_id = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID")
    if project_id:
        vertex_args["project_id"] = project_id
    
    return _MockAnthropicClient(
        provider="vertex",
        region=region,
        config=vertex_args,
        headers=default_headers,
    )


def _create_direct_client(
    api_key: Optional[str],
    default_headers: dict,
    max_retries: int,
    timeout_ms: int,
) -> Any:
    client_config = {
        "api_key": api_key,
        "max_retries": max_retries,
        "timeout": timeout_ms,
        "default_headers": default_headers,
    }
    
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    if base_url:
        client_config["base_url"] = base_url
    
    return _MockAnthropicClient(
        provider="direct",
        config=client_config,
        headers=default_headers,
    )


def _get_custom_headers() -> dict:
    custom_headers = {}
    custom_headers_env = os.environ.get("ANTHROPIC_CUSTOM_HEADERS")
    
    if not custom_headers_env:
        return custom_headers
    
    header_strings = custom_headers_env.split("\n")
    
    for header_string in header_strings:
        if not header_string.strip():
            continue
        
        colon_idx = header_string.index(":")
        if colon_idx == -1:
            continue
        name = header_string[:colon_idx].strip()
        value = header_string[colon_idx + 1:].strip()
        if name:
            custom_headers[name] = value
    
    return custom_headers


class _MockAnthropicClient:
    """
    Mock Anthropic client for placeholder implementation.
    In production, this would be replaced with actual SDK clients
    (AnthropicBedrock, AnthropicFoundry, AnthropicVertex, or Anthropic).
    """
    
    def __init__(
        self,
        provider: str,
        config: Optional[dict] = None,
        headers: Optional[dict] = None,
        region: Optional[str] = None,
    ):
        self.provider = provider
        self.config = config or {}
        self.headers = headers or {}
        self.region = region
    
    def __repr__(self) -> str:
        return f"_MockAnthropicClient(provider={self.provider}, region={self.region})"
