"""
Bootstrap service for fetching and caching Claude CLI bootstrap data.

This module provides functionality to fetch bootstrap configuration from the API
and cache it locally to avoid redundant network calls on every startup.
"""

import os
import random
import logging
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List, Callable, Awaitable

import httpx

logger = logging.getLogger(__name__)

# OAuth configuration constants
OAUTH_BETA_HEADER = "oauth-2025-04-20"
CLAUDE_AI_INFERENCE_SCOPE = "user:inference"
CLAUDE_AI_PROFILE_SCOPE = "user:profile"

# Retry configuration
BASE_DELAY_MS = 500
MAX_DELAY_MS = 32000
DEFAULT_TIMEOUT_SECONDS = 5


def _is_env_truthy(env_var: Optional[str]) -> bool:
    """Check if an environment variable is set to a truthy value."""
    if not env_var:
        return False
    return env_var.lower() in ("true", "1", "yes")


def _get_oauth_config() -> Dict[str, str]:
    """
    Get OAuth configuration based on environment.
    
    Returns the appropriate BASE_API_URL and other OAuth settings
    based on whether we're using prod, staging, or local.
    """
    # Check for custom OAuth URL override (FedStart/PubSec deployments)
    custom_oauth_url = os.environ.get("CLAUDE_CODE_CUSTOM_OAUTH_URL")
    if custom_oauth_url:
        base = custom_oauth_url.rstrip("/")
        return {
            "BASE_API_URL": base,
            "TOKEN_URL": f"{base}/v1/oauth/token",
        }
    
    # Check for local development
    user_type = os.environ.get("USER_TYPE", "")
    if user_type == "ant" and _is_env_truthy(os.environ.get("USE_LOCAL_OAUTH")):
        api_base = os.environ.get("CLAUDE_LOCAL_OAUTH_API_BASE", "http://localhost:8000")
        return {
            "BASE_API_URL": api_base,
            "TOKEN_URL": f"{api_base}/v1/oauth/token",
        }
    
    if user_type == "ant" and _is_env_truthy(os.environ.get("USE_STAGING_OAUTH")):
        return {
            "BASE_API_URL": "https://api-staging.anthropic.com",
            "TOKEN_URL": "https://platform.staging.ant.dev/v1/oauth/token",
        }
    
    # Production default
    return {
        "BASE_API_URL": "https://api.anthropic.com",
        "TOKEN_URL": "https://platform.claude.com/v1/oauth/token",
    }


def _get_api_provider() -> str:
    """Get the current API provider (firstParty, bedrock, vertex, foundry)."""
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_BEDROCK")):
        return "bedrock"
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_VERTEX")):
        return "vertex"
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_USE_FOUNDRY")):
        return "foundry"
    return "firstParty"


def _is_essential_traffic_only() -> bool:
    """Check if essential traffic only mode is enabled."""
    return _is_env_truthy(os.environ.get("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"))


# OAuth token management (simplified from TypeScript - in production would use secure storage)
_oauth_tokens_cache: Optional[Dict[str, Any]] = None


def get_oauth_tokens() -> Optional[Dict[str, Any]]:
    """Get cached OAuth tokens."""
    global _oauth_tokens_cache
    return _oauth_tokens_cache


def set_oauth_tokens(tokens: Dict[str, Any]) -> None:
    """Set OAuth tokens in cache."""
    global _oauth_tokens_cache
    _oauth_tokens_cache = tokens


def has_profile_scope() -> bool:
    """Check if the current OAuth token has the user:profile scope."""
    tokens = get_oauth_tokens()
    if not tokens:
        return False
    scopes = tokens.get("scopes", [])
    return CLAUDE_AI_PROFILE_SCOPE in scopes


def get_anthropic_api_key() -> Optional[str]:
    """Get the configured Anthropic API key."""
    # Check environment variable first
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return api_key
    
    # In production, would check keychain, config, etc.
    return None


def _is_oauth_token_revoked_error(error: Dict[str, Any]) -> bool:
    """Check if error indicates OAuth token has been revoked."""
    status = error.get("status")
    message = error.get("message", "")
    return status == 403 and "OAuth token has been revoked" in message


def _should_retry_on_auth_error(error: Dict[str, Any], also_403_revoked: bool = False) -> bool:
    """Determine if the error should trigger an auth retry."""
    status = error.get("status")
    
    # 401 always triggers retry
    if status == 401:
        return True
    
    # 403 with revoked token if enabled
    if also_403_revoked and status == 403:
        message = error.get("message", "")
        if "OAuth token has been revoked" in message:
            return True
    
    return False


def _parse_httpx_error(error: Exception) -> Dict[str, Any]:
    """Parse an httpx error into a standard error dict."""
    result: Dict[str, Any] = {
        "type": type(error).__name__,
        "message": str(error),
    }
    
    if isinstance(error, httpx.HTTPStatusError):
        result["status"] = error.response.status_code
        try:
            error_data = error.response.json()
            if isinstance(error_data, dict):
                result["message"] = error_data.get("error", {}).get("message", str(error))
            elif isinstance(error_data, str):
                result["message"] = error_data
        except Exception:
            result["message"] = str(error)
    elif isinstance(error, httpx.TimeoutException):
        result["message"] = "Request timed out"
    
    return result


async def _refresh_oauth_token() -> bool:
    """
    Handle OAuth 401 error by refreshing the token.
    
    In production, this would:
    1. Clear token cache
    2. Read fresh tokens from secure storage
    3. Check if keychain has different (already refreshed) token
    4. If same token, force refresh using refresh token
    
    Returns True if a valid token is now available, False otherwise.
    """
    global _oauth_tokens_cache
    
    # Clear cache to force re-read from secure storage
    _oauth_tokens_cache = None
    
    # Re-check tokens after cache clear
    tokens = get_oauth_tokens()
    if not tokens:
        return False
    
    # Check if another process already refreshed (different token in storage)
    failed_access_token = tokens.get("accessToken")
    if not failed_access_token:
        return False
    
    # If token changed in storage, we're good
    current_tokens = get_oauth_tokens()
    if current_tokens and current_tokens.get("accessToken") != failed_access_token:
        logger.debug("[Bootstrap] OAuth token refreshed by another process")
        return True
    
    # Same token - need to force refresh
    refresh_token = tokens.get("refreshToken")
    if not refresh_token:
        return False
    
    # In production, would call refresh OAuth token endpoint
    # For now, return False indicating refresh not available
    logger.debug("[Bootstrap] OAuth token refresh not available in this context")
    return False


async def with_oauth401_retry(
    request: Callable[[], Awaitable[httpx.Response]],
    also_403_revoked: bool = False,
) -> httpx.Response:
    """
    Wrapper that handles OAuth 401 errors by force-refreshing the token and retrying once.
    
    Addresses clock drift scenarios where the local expiration check disagrees with the server.
    The request closure is called again on retry, so it should re-read auth to pick up the
    refreshed token.
    
    Args:
        request: Async function that makes the HTTP request
        also_403_revoked: Also retry on 403 with "OAuth token has been revoked" body
        
    Returns:
        Response from the request
        
    Raises:
        Exception: If the error is not auth-related or retry fails
    """
    try:
        return await request()
    except Exception as e:
        error = _parse_httpx_error(e)
        
        if not _should_retry_on_auth_error(error, also_403_revoked):
            raise
        
        # Check if we have a token to refresh
        tokens = get_oauth_tokens()
        if not tokens or not tokens.get("accessToken"):
            raise
        
        # Try to refresh the token
        refreshed = await _refresh_oauth_token()
        if not refreshed:
            raise
        
        # Retry the request
        return await request()


def _get_retry_delay(attempt: int, retry_after_header: Optional[str] = None) -> float:
    """Calculate retry delay with exponential backoff and jitter."""
    if retry_after_header:
        try:
            seconds = int(retry_after_header)
            if seconds > 0:
                return seconds * 1000
        except ValueError:
            pass
    
    base_delay = min(BASE_DELAY_MS * (2 ** (attempt - 1)), MAX_DELAY_MS)
    jitter = random.random() * 0.25 * base_delay
    return base_delay + jitter


def _deep_equal(a: Any, b: Any) -> bool:
    """Deep equality check for comparing cached config."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(_deep_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(_deep_equal(a[i], b[i]) for i in range(len(a)))
    return a == b


@dataclass
class ModelOption:
    """Represents an additional model option from bootstrap."""
    model: str
    name: str
    description: str
    value: str = ""
    label: str = ""
    
    def __post_init__(self):
        if not self.value:
            self.value = self.model
        if not self.label:
            self.label = self.name


@dataclass
class BootstrapConfig:
    """Bootstrap configuration data."""
    client_data: Optional[Dict[str, Any]] = None
    additional_model_options: List[ModelOption] = field(default_factory=list)


class BootstrapService:
    """
    Service for fetching and caching bootstrap configuration.
    
    Implements a singleton pattern to ensure only one instance fetches
    and caches bootstrap data.
    """
    _instance: Optional["BootstrapService"] = None
    _cached_config: Optional[BootstrapConfig] = None
    _cache_loaded: bool = False
    
    def __new__(cls) -> "BootstrapService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "BootstrapService":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def fetch_bootstrap_api(self) -> Optional[BootstrapConfig]:
        """
        Fetch bootstrap data from the API.
        
        OAuth is preferred (requires user:profile scope). Falls back to API key
        auth for console users.
        
        Returns:
            BootstrapConfig if successful, None otherwise
        """
        # Check for essential traffic restriction
        if _is_essential_traffic_only():
            logger.debug("[Bootstrap] Skipped: Nonessential traffic disabled")
            return None
        
        # Check for third-party provider
        if _get_api_provider() != "firstParty":
            logger.debug("[Bootstrap] Skipped: 3P provider")
            return None
        
        # Check for usable OAuth or API key
        api_key = get_anthropic_api_key()
        tokens = get_oauth_tokens()
        has_usable_oauth = tokens and tokens.get("accessToken") and has_profile_scope()
        
        if not has_usable_oauth and not api_key:
            logger.debug("[Bootstrap] Skipped: no usable OAuth or API key")
            return None
        
        oauth_config = _get_oauth_config()
        endpoint = f"{oauth_config['BASE_API_URL']}/api/claude_cli/bootstrap"
        
        async def make_request() -> httpx.Response:
            # Re-read OAuth each call so the retry picks up the refreshed token
            current_tokens = get_oauth_tokens()
            
            auth_headers: Dict[str, str] = {}
            if current_tokens and current_tokens.get("accessToken") and has_profile_scope():
                auth_headers = {
                    "Authorization": f"Bearer {current_tokens['accessToken']}",
                    "anthropic-beta": OAUTH_BETA_HEADER,
                }
            elif api_key:
                auth_headers = {"x-api-key": api_key}
            else:
                logger.debug("[Bootstrap] No auth available on retry, aborting")
                raise Exception("No authentication available")
            
            logger.debug("[Bootstrap] Fetching")
            
            user_agent = "claude-code/cli (python)"
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                return await client.get(
                    endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": user_agent,
                        **auth_headers,
                    },
                )
        
        try:
            response = await with_oauth401_retry(make_request)
            
            if response.status_code != 200:
                logger.debug(f"[Bootstrap] Fetch failed: {response.status_code}")
                return None
            
            data = response.json()
            
            # Parse response
            client_data = data.get("client_data")
            additional_model_options_raw = data.get("additional_model_options") or []
            
            additional_model_options = []
            for opt in additional_model_options_raw:
                if isinstance(opt, dict):
                    additional_model_options.append(ModelOption(
                        model=opt.get("model", ""),
                        name=opt.get("name", ""),
                        description=opt.get("description", ""),
                        value=opt.get("value", opt.get("model", "")),
                        label=opt.get("label", opt.get("name", "")),
                    ))
            
            return BootstrapConfig(
                client_data=client_data,
                additional_model_options=additional_model_options,
            )
            
        except Exception as e:
            error_type = type(e).__name__
            if isinstance(e, httpx.HTTPStatusError):
                error_msg = f"{e.response.status_code}"
            else:
                error_msg = str(e)
            logger.debug(f"[Bootstrap] Fetch failed: {error_type}: {error_msg}")
            raise
    
    async def fetch_bootstrap_data(self) -> Optional[BootstrapConfig]:
        """
        Fetch bootstrap data from the API and persist to disk cache.
        
        Only persists if data actually changed to avoid unnecessary config writes.
        
        Returns:
            BootstrapConfig if successful, None otherwise
        """
        try:
            response = await self.fetch_bootstrap_api()
            if not response:
                return None
            
            client_data = response.client_data
            additional_model_options = response.additional_model_options
            
            # Check if data changed (skip write if cache unchanged)
            if self._cached_config:
                cached_client_data = self._cached_config.client_data
                cached_model_options = [
                    {"model": opt.model, "name": opt.name, "description": opt.description}
                    for opt in self._cached_config.additional_model_options
                ]
                new_model_options = [
                    {"model": opt.model, "name": opt.name, "description": opt.description}
                    for opt in additional_model_options
                ]
                
                if (_deep_equal(cached_client_data, client_data) and
                    _deep_equal(cached_model_options, new_model_options)):
                    logger.debug("[Bootstrap] Cache unchanged, skipping write")
                    return response
            
            logger.debug("[Bootstrap] Cache updated, persisting to disk")
            await self._save_to_cache(response)
            self._cached_config = response
            return response
            
        except Exception as e:
            logger.error(f"[Bootstrap] Error fetching bootstrap data: {e}")
            return None
    
    async def _save_to_cache(self, config: BootstrapConfig) -> None:
        """
        Save bootstrap config to disk cache.
        
        In production, this would save to ~/.claude/settings.json or similar.
        For now, just update the in-memory cache.
        """
        # In production: would save to global config file
        # saveGlobalConfig(current => ({
        #     ...current,
        #     clientDataCache: clientData,
        #     additionalModelOptionsCache: additionalModelOptions,
        # }))
        self._cached_config = config
        self._cache_loaded = True
    
    def get_cached_config(self) -> Optional[BootstrapConfig]:
        """Get the cached bootstrap configuration."""
        return self._cached_config if self._cache_loaded else None
    
    def clear_cache(self) -> None:
        """Clear the cached bootstrap configuration."""
        self._cached_config = None
        self._cache_loaded = False


async def fetch_bootstrap_data() -> Optional[BootstrapConfig]:
    """
    Convenience function to fetch bootstrap data using the singleton service.
    
    Returns:
        BootstrapConfig if successful, None otherwise
    """
    service = BootstrapService.get_instance()
    return await service.fetch_bootstrap_data()


def get_bootstrap_config() -> Optional[BootstrapConfig]:
    """
    Get the cached bootstrap configuration.
    
    Returns:
        BootstrapConfig if cached, None otherwise
    """
    service = BootstrapService.get_instance()
    return service.get_cached_config()
