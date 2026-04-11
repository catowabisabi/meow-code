"""OAuth configuration supporting prod/staging/local environments."""

import os
from dataclasses import dataclass
from typing import Literal, Optional


# Environment variable helpers
def _is_env_truthy(env_var: Optional[str]) -> bool:
    """Check if an environment variable is set to a truthy value."""
    if not env_var:
        return False
    return env_var.lower() in ("1", "true", "yes", "on")


# OAuth config type
OauthConfigType = Literal["prod", "staging", "local"]


def _get_oauth_config_type() -> OauthConfigType:
    """Determine OAuth config type based on environment."""
    if os.environ.get("USER_TYPE") == "ant":
        if _is_env_truthy(os.environ.get("USE_LOCAL_OAUTH")):
            return "local"
        if _is_env_truthy(os.environ.get("USE_STAGING_OAUTH")):
            return "staging"
    return "prod"


def file_suffix_for_oauth_config() -> str:
    """Get the file suffix for the current OAuth config."""
    if os.environ.get("CLAUDE_CODE_CUSTOM_OAUTH_URL"):
        return "-custom-oauth"
    config_type = _get_oauth_config_type()
    if config_type == "local":
        return "-local-oauth"
    elif config_type == "staging":
        return "-staging-oauth"
    return ""  # prod has no suffix


# OAuth scopes
CLAUDE_AI_INFERENCE_SCOPE = "user:inference"
CLAUDE_AI_PROFILE_SCOPE = "user:profile"
CONSOLE_SCOPE = "org:create_api_key"
OAUTH_BETA_HEADER = "oauth-2025-04-20"

# Console OAuth scopes - for API key creation via Console
CONSOLE_OAUTH_SCOPES = [
    CONSOLE_SCOPE,
    CLAUDE_AI_PROFILE_SCOPE,
]

# Claude.ai OAuth scopes - for Claude.ai subscribers (Pro/Max/Team/Enterprise)
CLAUDE_AI_OAUTH_SCOPES = [
    CLAUDE_AI_PROFILE_SCOPE,
    CLAUDE_AI_INFERENCE_SCOPE,
    "user:sessions:claude_code",
    "user:mcp_servers",
    "user:file_upload",
]

# All OAuth scopes - union of all scopes used in Claude CLI
ALL_OAUTH_SCOPES = list(set(CONSOLE_OAUTH_SCOPES + CLAUDE_AI_OAUTH_SCOPES))


# Allowed base URLs for CLAUDE_CODE_CUSTOM_OAUTH_URL override.
# Only FedStart/PubSec deployments are permitted to prevent OAuth tokens
# from being sent to arbitrary endpoints.
ALLOWED_OAUTH_BASE_URLS = [
    "https://beacon.claude-ai.staging.ant.dev",
    "https://claude.fedstart.com",
    "https://claude-staging.fedstart.com",
]


@dataclass
class OauthConfig:
    """OAuth configuration structure."""
    base_api_url: str
    console_authorize_url: str
    claude_ai_authorize_url: str
    claude_ai_origin: str
    token_url: str
    api_key_url: str
    roles_url: str
    console_success_url: str
    claudenai_success_url: str
    manual_redirect_url: str
    client_id: str
    oauth_file_suffix: str
    mcp_proxy_url: str
    mcp_proxy_path: str


# Production OAuth configuration - Used in normal operation
PROD_OAUTH_CONFIG = OauthConfig(
    base_api_url="https://api.anthropic.com",
    console_authorize_url="https://platform.claude.com/oauth/authorize",
    # Bounces through claude.com/cai/* so CLI sign-ins connect to claude.com
    # visits for attribution. 307s to claude.ai/oauth/authorize in two hops.
    claude_ai_authorize_url="https://claude.com/cai/oauth/authorize",
    claude_ai_origin="https://claude.ai",
    token_url="https://platform.claude.com/v1/oauth/token",
    api_key_url="https://api.anthropic.com/api/oauth/claude_cli/create_api_key",
    roles_url="https://api.anthropic.com/api/oauth/claude_cli/roles",
    console_success_url="https://platform.claude.com/buy_credits?returnUrl=/oauth/code/success%3Fapp%3Dclaude-code",
    claudenai_success_url="https://platform.claude.com/oauth/code/success?app=claude-code",
    manual_redirect_url="https://platform.claude.com/oauth/code/callback",
    client_id="9d1c250a-e61b-44d9-88ed-5944d1962f5e",
    oauth_file_suffix="",
    mcp_proxy_url="https://mcp-proxy.anthropic.com",
    mcp_proxy_path="/v1/mcp/{server_id}",
)

# Staging OAuth configuration - only included in ant builds with staging flag
# Uses literal check for dead code elimination
def _get_staging_oauth_config() -> Optional[OauthConfig]:
    if os.environ.get("USER_TYPE") == "ant":
        return OauthConfig(
            base_api_url="https://api-staging.anthropic.com",
            console_authorize_url="https://platform.staging.ant.dev/oauth/authorize",
            claude_ai_authorize_url="https://claude-ai.staging.ant.dev/oauth/authorize",
            claude_ai_origin="https://claude-ai.staging.ant.dev",
            token_url="https://platform.staging.ant.dev/v1/oauth/token",
            api_key_url="https://api-staging.anthropic.com/api/oauth/claude_cli/create_api_key",
            roles_url="https://api-staging.anthropic.com/api/oauth/claude_cli/roles",
            console_success_url="https://platform.staging.ant.dev/buy_credits?returnUrl=/oauth/code/success%3Fapp%3Dclaude-code",
            claudenai_success_url="https://platform.staging.ant.dev/oauth/code/success?app%3Dclaude-code",
            manual_redirect_url="https://platform.staging.ant.dev/oauth/code/callback",
            client_id="22422756-60c9-4084-8eb7-27705fd5cf9a",
            oauth_file_suffix="-staging-oauth",
            mcp_proxy_url="https://mcp-proxy-staging.anthropic.com",
            mcp_proxy_path="/v1/mcp/{server_id}",
        )
    return None


def _get_local_oauth_config() -> OauthConfig:
    """Get local OAuth config for development."""
    # Three local dev servers: :8000 api-proxy (`api dev start -g ccr`),
    # :4000 claude-ai frontend, :3000 Console frontend. Env vars let
    # scripts/claude-localhost override if your layout differs.
    api_base = os.environ.get("CLAUDE_LOCAL_OAUTH_API_BASE", "http://localhost:8000").rstrip("/")
    apps_base = os.environ.get("CLAUDE_LOCAL_OAUTH_APPS_BASE", "http://localhost:4000").rstrip("/")
    console_base = os.environ.get("CLAUDE_LOCAL_OAUTH_CONSOLE_BASE", "http://localhost:3000").rstrip("/")
    
    return OauthConfig(
        base_api_url=api_base,
        console_authorize_url=f"{console_base}/oauth/authorize",
        claude_ai_authorize_url=f"{apps_base}/oauth/authorize",
        claude_ai_origin=apps_base,
        token_url=f"{api_base}/v1/oauth/token",
        api_key_url=f"{api_base}/api/oauth/claude_cli/create_api_key",
        roles_url=f"{api_base}/api/oauth/claude_cli/roles",
        console_success_url=f"{console_base}/buy_credits?returnUrl=/oauth/code/success%3Fapp%3Dclaude-code",
        claudenai_success_url=f"{console_base}/oauth/code/success?app=claude-code",
        manual_redirect_url=f"{console_base}/oauth/code/callback",
        client_id="22422756-60c9-4084-8eb7-27705fd5cf9a",
        oauth_file_suffix="-local-oauth",
        mcp_proxy_url="http://localhost:8205",
        mcp_proxy_path="/v1/toolbox/shttp/mcp/{server_id}",
    )


def get_oauth_config() -> OauthConfig:
    """
    Get the OAuth configuration based on environment.
    
    Default to prod config, override with test/staging if enabled.
    Supports CLAUDE_CODE_CUSTOM_OAUTH_URL for FedStart deployments.
    Supports CLAUDE_CODE_OAUTH_CLIENT_ID for Xcode integration.
    """
    config_type = _get_oauth_config_type()
    
    if config_type == "local":
        config = _get_local_oauth_config()
    elif config_type == "staging":
        staging_config = _get_staging_oauth_config()
        config = staging_config if staging_config else PROD_OAUTH_CONFIG
    else:
        config = PROD_OAUTH_CONFIG
    
    # Allow overriding all OAuth URLs to point to an approved FedStart deployment.
    # Only allowlisted base URLs are accepted to prevent credential leakage.
    oauth_base_url = os.environ.get("CLAUDE_CODE_CUSTOM_OAUTH_URL")
    if oauth_base_url:
        base = oauth_base_url.rstrip("/")
        if base not in ALLOWED_OAUTH_BASE_URLS:
            raise ValueError(
                "CLAUDE_CODE_CUSTOM_OAUTH_URL is not an approved endpoint."
            )
        config = OauthConfig(
            base_api_url=base,
            console_authorize_url=f"{base}/oauth/authorize",
            claude_ai_authorize_url=f"{base}/oauth/authorize",
            claude_ai_origin=base,
            token_url=f"{base}/v1/oauth/token",
            api_key_url=f"{base}/api/oauth/claude_cli/create_api_key",
            roles_url=f"{base}/api/oauth/claude_cli/roles",
            console_success_url=f"{base}/oauth/code/success?app=claude-code",
            claudenai_success_url=f"{base}/oauth/code/success?app=claude-code",
            manual_redirect_url=f"{base}/oauth/code/callback",
            client_id=config.client_id,
            oauth_file_suffix="-custom-oauth",
            mcp_proxy_url=config.mcp_proxy_url,
            mcp_proxy_path=config.mcp_proxy_path,
        )
    
    # Allow CLIENT_ID override via environment variable (e.g., for Xcode integration)
    client_id_override = os.environ.get("CLAUDE_CODE_OAUTH_CLIENT_ID")
    if client_id_override:
        config = OauthConfig(
            base_api_url=config.base_api_url,
            console_authorize_url=config.console_authorize_url,
            claude_ai_authorize_url=config.claude_ai_authorize_url,
            claude_ai_origin=config.claude_ai_origin,
            token_url=config.token_url,
            api_key_url=config.api_key_url,
            roles_url=config.roles_url,
            console_success_url=config.console_success_url,
            claudenai_success_url=config.claudenai_success_url,
            manual_redirect_url=config.manual_redirect_url,
            client_id=client_id_override,
            oauth_file_suffix=config.oauth_file_suffix,
            mcp_proxy_url=config.mcp_proxy_url,
            mcp_proxy_path=config.mcp_proxy_path,
        )
    
    return config


# Client ID Metadata Document URL for MCP OAuth (CIMD / SEP-991).
# When an MCP auth server advertises client_id_metadata_document_supported: true,
# Claude Code uses this URL as its client_id instead of Dynamic Client Registration.
# The URL must point to a JSON document hosted by Anthropic.
# See: https://datatracker.ietf.org/doc/html/draft-ietf-oauth-client-id-metadata-document-00
MCP_CLIENT_METADATA_URL = "https://claude.ai/oauth/claude-code-client-metadata"
