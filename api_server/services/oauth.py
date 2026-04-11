"""
OAuth 2.0 PKCE Flow Service

Implements the OAuth 2.0 authorization code flow with PKCE (Proof Key for Code Exchange).
Supports both automatic (browser redirect) and manual (copy-paste) auth code flows.
"""

import base64
import hashlib
import os
import secrets
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

import httpx
from pydantic import BaseModel


# =============================================================================
# PKCE Crypto Utilities
# =============================================================================

def generate_code_verifier() -> str:
    """
    Generate a random code verifier for PKCE.
    
    Returns:
        A random 32-byte string encoded as base64url.
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("utf-8")


def generate_code_challenge(verifier: str) -> str:
    """
    Generate a code challenge from a code verifier using SHA256.
    
    Args:
        verifier: The code verifier string
        
    Returns:
        The base64url-encoded SHA256 hash of the verifier
    """
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")


def generate_state() -> str:
    """
    Generate a random state parameter for CSRF protection.
    
    Returns:
        A random 32-byte string encoded as base64url.
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("utf-8")


# =============================================================================
# OAuth Configuration
# =============================================================================

@dataclass
class OAuthConfig:
    """OAuth configuration settings."""
    client_id: str = "claude_code"
    authorize_url: str = "https://auth.claude.ai/authorize"
    token_url: str = "https://auth.claude.ai/oauth/token"
    profile_url: str = "https://api.claude.ai/api/oauth/profile"
    base_api_url: str = "https://api.claude.ai"
    manual_redirect_url: str = "https://claude.ai/code/callback"
    claudeai_success_url: str = "https://claude.ai/code/success"
    console_success_url: str = "https://console.anthropic.com/code/success"
    roles_url: str = "https://api.claude.ai/api/oauth/roles"
    api_key_url: str = "https://api.claude.ai/api/oauth/api-key"


# Default OAuth scopes
ALL_OAUTH_SCOPES = [
    "openid",
    "profile",
    "email",
    "account:read",
    "organization:read",
    "claude.ai:inference",
]

CLAUDE_AI_INFERENCE_SCOPE = "claude.ai: inference"
CLAUDE_AI_OAUTH_SCOPES = [
    "openid",
    "profile",
    "email",
    "account:read",
    "organization:read",
    "claude.ai: inference",
]

# Token expiry buffer (5 minutes in ms)
TOKEN_EXPIRY_BUFFER_MS = 5 * 60 * 1000


def get_oauth_config() -> OAuthConfig:
    """Get OAuth configuration from environment or defaults."""
    return OAuthConfig(
        client_id=os.environ.get("CLAUDE_CODE_OAUTH_CLIENT_ID", "claude_code"),
        authorize_url=os.environ.get(
            "CLAUDE_AI_AUTHORIZE_URL",
            "https://auth.claude.ai/authorize"
        ),
        token_url=os.environ.get(
            "CLAUDE_CODE_TOKEN_URL",
            "https://auth.claude.ai/oauth/token"
        ),
        profile_url=os.environ.get(
            "CLAUDE_CODE_PROFILE_URL",
            "https://api.claude.ai/api/oauth/profile"
        ),
        base_api_url=os.environ.get(
            "CLAUDE_CODE_API_BASE_URL",
            "https://api.claude.ai"
        ),
    )


# =============================================================================
# Data Models
# =============================================================================

class SubscriptionType(str, Enum):
    """Subscription type enumeration."""
    MAX = "max"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    TEAM = "team"
    FREE = "free"


class RateLimitTier(str, Enum):
    """Rate limit tier enumeration."""
    STANDARD = "standard"
    PLUS = "plus"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class BillingType(str, Enum):
    """Billing type enumeration."""
    FREE = "free"
    SUBSCRIPTION = "subscription"
    OVERAGE = "overage"


@dataclass
class OAuthTokens:
    """OAuth token response."""
    access_token: str
    refresh_token: Optional[str]
    expires_at: float
    scopes: List[str]
    subscription_type: Optional[SubscriptionType] = None
    rate_limit_tier: Optional[RateLimitTier] = None
    profile: Optional[Dict[str, Any]] = None
    token_account: Optional[Dict[str, Any]] = None


@dataclass
class TokenAccount:
    """Token account information."""
    uuid: str
    email_address: str
    organization_uuid: Optional[str] = None


@dataclass
class OAuthProfileResponse:
    """OAuth profile response from API."""
    account: Optional[Dict[str, Any]] = None
    organization: Optional[Dict[str, Any]] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class OAuthTokenExchangeResponse:
    """OAuth token exchange response."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int = 3600
    scope: Optional[str] = None
    account: Optional[Dict[str, Any]] = None
    organization: Optional[Dict[str, Any]] = None


# =============================================================================
# Auth Code Listener
# =============================================================================

class AuthCodeListener:
    """
    Local HTTP server that listens for OAuth authorization code redirects.
    
    When the user authorizes in their browser, the OAuth provider redirects to:
    http://localhost:[port]/callback?code=AUTH_CODE&state=STATE
    
    This server captures that redirect and extracts the auth code.
    """
    
    def __init__(self, callback_path: str = "/callback"):
        self._callback_path = callback_path
        self._server: Optional[Any] = None
        self._port: int = 0
        self._promise_resolver: Optional[Callable[[str], None]] = None
        self._promise_rejecter: Optional[Callable[[Exception], None]] = None
        self._expected_state: Optional[str] = None
        self._pending_response: Optional[Any] = None
        self._resolved = False

    async def start(self, port: int = 0) -> int:
        """
        Start listening on the specified port (0 = OS-assigned).
        
        Args:
            port: Port to listen on (0 for OS assignment)
            
        Returns:
            The port number that was assigned
        """
        import asyncio
        
        async def handle_callback(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                request_line = await reader.readline()
                if not request_line:
                    writer.close()
                    return

                decoded = request_line.decode("utf-8", errors="replace")
                parts = decoded.split(" ")
                if len(parts) < 2:
                    writer.close()
                    return

                path = parts[1]
                parsed = urllib.parse.urlparse(path)
                query = urllib.parse.parse_qs(parsed.query)

                code = query.get("code", [None])[0]
                state = query.get("state", [None])[0]
                error = query.get("error", [None])[0]

                if error:
                    response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Type: text/html\r\n"
                        "\r\n"
                        "<html><body><h3>IdP login failed</h3><p>{}</p></body></html>".format(
                            self._escape_html(error)
                        )
                    )
                    writer.write(response.encode())
                    writer.close()
                    if self._promise_rejecter:
                        self._promise_rejecter(Exception(f"OAuth error: {error}"))
                    return

                if state != self._expected_state:
                    response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Type: text/html\r\n"
                        "\r\n"
                        "<html><body><h3>State mismatch</h3></body></html>"
                    )
                    writer.write(response.encode())
                    writer.close()
                    if self._promise_rejecter:
                        self._promise_rejecter(Exception("Invalid state parameter"))
                    return

                if not code:
                    response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Type: text/html\r\n"
                        "\r\n"
                        "<html><body><h3>Missing code</h3></body></html>"
                    )
                    writer.write(response.encode())
                    writer.close()
                    if self._promise_rejecter:
                        self._promise_rejecter(Exception("No authorization code received"))
                    return

                # Store response for redirect
                self._pending_response = writer
                
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html\r\n"
                    "\r\n"
                    "<html><body><h3>Login successful! You can close this window.</h3></body></html>"
                )
                writer.write(response.encode())
                writer.close()

                if self._promise_resolver and not self._resolved:
                    self._resolved = True
                    self._promise_resolver(code)

            except Exception as e:
                writer.close()
                if self._promise_rejecter and not self._resolved:
                    self._resolved = True
                    self._promise_rejecter(e)

        async def start_server() -> int:
            server = await asyncio.start_server(handle_callback, "127.0.0.1", port)
            return server

        self._server = await start_server()
        sock = self._server.sockets[0]
        self._port = sock.getsockname()[1]
        return self._port

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def get_port(self) -> int:
        """Get the listening port."""
        return self._port

    def has_pending_response(self) -> bool:
        """Check if there's a pending response for redirect."""
        return self._pending_response is not None

    async def wait_for_authorization(
        self,
        state: str,
        on_ready: Optional[Callable[[], None]] = None,
    ) -> str:
        """
        Wait for authorization code with state validation.
        
        Args:
            state: Expected state parameter
            on_ready: Callback when server is ready
            
        Returns:
            The authorization code
        """
        import asyncio
        
        self._expected_state = state
        
        if on_ready:
            on_ready()
        
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        def resolver(code: str) -> None:
            if not future.done():
                future.set_result(code)
        
        def rejecter(error: Exception) -> None:
            if not future.done():
                future.set_result(None)  # type: ignore
        
        self._promise_resolver = resolver
        self._promise_rejecter = rejecter
        
        try:
            result = await future
            if result is None:
                raise Exception("Authorization failed")
            return result
        except Exception as e:
            raise e

    def handle_success_redirect(self, scopes: List[str]) -> None:
        """
        Handle success by redirecting the browser.
        
        Args:
            scopes: The OAuth scopes that were granted
        """
        if CLAUDE_AI_INFERENCE_SCOPE in scopes:
            # Claude.ai auth successful with inference scope
            pass
        else:
            # Console auth successful
            pass
        
        if self._pending_response:
            pass

    def handle_error_redirect(self) -> None:
        """Handle error by sending a redirect."""
        if self._pending_response:
            pass

    def close(self) -> None:
        """Close the listener server."""
        if self._server:
            self._server.close()
            self._server = None


# =============================================================================
# OAuth Client
# =============================================================================

def parse_scopes(scope_string: Optional[str]) -> List[str]:
    """Parse scope string into list."""
    return scope_string.split(" ") if scope_string else []


def build_auth_url(
    code_challenge: str,
    state: str,
    port: int,
    is_manual: bool = False,
    login_with_claude_ai: bool = True,
    inference_only: bool = False,
    org_uuid: Optional[str] = None,
    login_hint: Optional[str] = None,
    login_method: Optional[str] = None,
) -> str:
    """
    Build the OAuth authorization URL.
    
    Args:
        code_challenge: PKCE code challenge
        state: State parameter for CSRF protection
        port: Callback port
        is_manual: Use manual redirect URL
        login_with_claude_ai: Use Claude.ai auth URL
        inference_only: Request inference-only scope
        org_uuid: Optional organization UUID
        login_hint: Optional email hint
        login_method: Optional login method (sso, magic_link, google)
        
    Returns:
        The authorization URL
    """
    config = get_oauth_config()
    
    if login_with_claude_ai:
        auth_url_base = config.authorize_url
    else:
        auth_url_base = config.authorize_url.replace("auth.claude.ai", "console.anthropic.com")

    auth_url = urllib.parse.urlparse(auth_url_base)
    
    scopes = [CLAUDE_AI_INFERENCE_SCOPE] if inference_only else ALL_OAUTH_SCOPES
    
    params: Dict[str, str] = {
        "code": "true",  # Tell login page to show Claude Max upsell
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": config.manual_redirect_url if is_manual else f"http://localhost:{port}/callback",
        "scope": " ".join(scopes),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    
    if org_uuid:
        params["orgUUID"] = org_uuid
    if login_hint:
        params["login_hint"] = login_hint
    if login_method:
        params["login_method"] = login_method
    
    return urllib.parse.urlunparse((
        auth_url.scheme,
        auth_url.netloc,
        auth_url.path,
        "",
        urllib.parse.urlencode(params),
        "",
    ))


async def exchange_code_for_tokens(
    authorization_code: str,
    state: str,
    code_verifier: str,
    port: int,
    use_manual_redirect: bool = False,
    expires_in: Optional[int] = None,
) -> OAuthTokenExchangeResponse:
    """
    Exchange authorization code for tokens.
    
    Args:
        authorization_code: The authorization code
        state: State parameter
        code_verifier: PKCE code verifier
        port: Callback port
        use_manual_redirect: Use manual redirect URI
        expires_in: Optional token lifetime
        
    Returns:
        Token exchange response
    """
    config = get_oauth_config()
    
    request_body: Dict[str, Any] = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": config.manual_redirect_url if use_manual_redirect else f"http://localhost:{port}/callback",
        "client_id": config.client_id,
        "code_verifier": code_verifier,
        "state": state,
    }
    
    if expires_in is not None:
        request_body["expires_in"] = expires_in
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            config.token_url,
            json=request_body,
            headers={"Content-Type": "application/json"},
        )
        
        if response.status_code == 401:
            raise Exception("Authentication failed: Invalid authorization code")
        if response.status_code != 200:
            raise Exception(f"Token exchange failed ({response.status_code}): {response.status_text}")
        
        data = response.json()
        return OAuthTokenExchangeResponse(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 3600),
            scope=data.get("scope"),
            account=data.get("account"),
            organization=data.get("organization"),
        )


async def refresh_oauth_token(
    refresh_token: str,
    scopes: Optional[List[str]] = None,
) -> OAuthTokens:
    """
    Refresh an OAuth token.
    
    Args:
        refresh_token: The refresh token
        scopes: Optional requested scopes
        
    Returns:
        New OAuth tokens
    """
    config = get_oauth_config()
    
    request_body: Dict[str, Any] = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": config.client_id,
        "scope": " ".join(scopes or CLAUDE_AI_OAUTH_SCOPES),
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            config.token_url,
            json=request_body,
            headers={"Content-Type": "application/json"},
        )
        
        if response.status_code != 200:
            raise Exception(f"Token refresh failed: {response.status_text}")
        
        data = response.json()
        access_token = data.get("access_token", "")
        new_refresh_token = data.get("refresh_token", refresh_token)
        token_expires_in = data.get("expires_in", 3600)
        
        expires_at = time.time() * 1000 + token_expires_in * 1000
        token_scopes = parse_scopes(data.get("scope"))
        
        # Fetch profile info
        profile_info = await fetch_profile_info(access_token)
        
        return OAuthTokens(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_at=expires_at,
            scopes=token_scopes,
            subscription_type=profile_info.get("subscription_type"),
            rate_limit_tier=profile_info.get("rate_limit_tier"),
        )


async def fetch_profile_info(access_token: str) -> Dict[str, Any]:
    """
    Fetch OAuth profile information.
    
    Args:
        access_token: The access token
        
    Returns:
        Profile info dict with subscription_type and rate_limit_tier
    """
    config = get_oauth_config()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                config.profile_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )
            
            if response.status_code != 200:
                return {"subscription_type": None, "rate_limit_tier": None}
            
            profile = response.json()
            org_type = profile.get("organization", {}).get("organization_type")
            
            # Map organization type to subscription type
            subscription_type: Optional[SubscriptionType] = None
            if org_type == "claude_max":
                subscription_type = SubscriptionType.MAX
            elif org_type == "claude_pro":
                subscription_type = SubscriptionType.PRO
            elif org_type == "claude_enterprise":
                subscription_type = SubscriptionType.ENTERPRISE
            elif org_type == "claude_team":
                subscription_type = SubscriptionType.TEAM
            
            return {
                "subscription_type": subscription_type,
                "rate_limit_tier": profile.get("organization", {}).get("rate_limit_tier"),
                "raw_profile": profile,
            }
    except Exception:
        return {"subscription_type": None, "rate_limit_tier": None}


def is_oauth_token_expired(expires_at: Optional[float]) -> bool:
    """
    Check if an OAuth token is expired or about to expire.
    
    Args:
        expires_at: Token expiry time in milliseconds
        
    Returns:
        True if expired or within buffer period
    """
    if expires_at is None:
        return False
    
    return (time.time() * 1000 + TOKEN_EXPIRY_BUFFER_MS) >= expires_at


# =============================================================================
# OAuth Service
# =============================================================================

class OAuthService:
    """
    Main OAuth service class that handles the OAuth 2.0 authorization code flow with PKCE.
    
    Supports two ways to get authorization codes:
    1. Automatic: Opens browser, redirects to localhost where we capture the code
    2. Manual: User manually copies and pastes the code (used in non-browser environments)
    """
    
    def __init__(self):
        self._code_verifier: str = ""
        self._auth_code_listener: Optional[AuthCodeListener] = None
        self._port: Optional[int] = None
        self._manual_auth_code_resolver: Optional[Callable[[str], None]] = None
        self._config = get_oauth_config()
    
    def _ensure_code_verifier(self) -> None:
        """Generate code verifier if not set."""
        if not self._code_verifier:
            self._code_verifier = generate_code_verifier()
    
    async def start_oauth_flow(
        self,
        auth_url_handler: Callable[[str, Optional[str]], Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> OAuthTokens:
        """
        Start the OAuth flow.
        
        Args:
            auth_url_handler: Callback to handle auth URLs (show manual option, open browser)
            options: Optional configuration
                - login_with_claude_ai: Use Claude.ai auth
                - inference_only: Request inference-only scope
                - expires_in: Token lifetime
                - org_uuid: Organization UUID
                - login_hint: Pre-populate email
                - login_method: Specific login method
                - skip_browser_open: Don't auto-open browser
                
        Returns:
            OAuth tokens
        """
        opts = options or {}
        
        # Create OAuth callback listener and start it
        self._auth_code_listener = AuthCodeListener()
        self._port = await self._auth_code_listener.start()
        
        # Generate PKCE values and state
        self._ensure_code_verifier()
        code_challenge = generate_code_challenge(self._code_verifier)
        state = generate_state()
        
        # Build auth URLs for both automatic and manual flows
        manual_flow_url = build_auth_url(
            code_challenge=code_challenge,
            state=state,
            port=self._port,
            is_manual=True,
            login_with_claude_ai=opts.get("login_with_claude_ai", True),
            inference_only=opts.get("inference_only", False),
            org_uuid=opts.get("org_uuid"),
            login_hint=opts.get("login_hint"),
            login_method=opts.get("login_method"),
        )
        
        automatic_flow_url = build_auth_url(
            code_challenge=code_challenge,
            state=state,
            port=self._port,
            is_manual=False,
            login_with_claude_ai=opts.get("login_with_claude_ai", True),
            inference_only=opts.get("inference_only", False),
            org_uuid=opts.get("org_uuid"),
            login_hint=opts.get("login_hint"),
            login_method=opts.get("login_method"),
        )
        
        # Wait for authorization code
        authorization_code = await self._wait_for_authorization_code(
            state,
            opts.get("skip_browser_open", False),
            auth_url_handler,
            manual_flow_url,
            automatic_flow_url,
        )
        
        # Check if automatic flow is still active
        is_automatic_flow = self._auth_code_listener.has_pending_response() if self._auth_code_listener else False
        
        try:
            # Exchange authorization code for tokens
            token_response = await exchange_code_for_tokens(
                authorization_code=authorization_code,
                state=state,
                code_verifier=self._code_verifier,
                port=self._port,
                use_manual_redirect=not is_automatic_flow,
                expires_in=opts.get("expires_in"),
            )
            
            # Fetch profile info
            profile_info = await fetch_profile_info(token_response.access_token)
            
            # Handle success redirect for automatic flow
            if is_automatic_flow and self._auth_code_listener:
                scopes = parse_scopes(token_response.scope)
                self._auth_code_listener.handle_success_redirect(scopes)
            
            return self._format_tokens(
                token_response,
                profile_info.get("subscription_type"),
                profile_info.get("rate_limit_tier"),
                profile_info.get("raw_profile"),
            )
        except Exception as e:
            # If we have a pending response, send an error redirect before closing
            if is_automatic_flow and self._auth_code_listener:
                self._auth_code_listener.handle_error_redirect()
            raise e
        finally:
            # Always cleanup
            if self._auth_code_listener:
                self._auth_code_listener.close()
    
    async def _wait_for_authorization_code(
        self,
        state: str,
        skip_browser_open: bool,
        auth_url_handler: Callable[[str, Optional[str]], Any],
        manual_flow_url: str,
        automatic_flow_url: str,
    ) -> str:
        """
        Wait for authorization code from either automatic or manual flow.
        
        Args:
            state: Expected state parameter
            skip_browser_open: Skip browser open
            auth_url_handler: Handler for auth URLs
            manual_flow_url: Manual flow URL
            automatic_flow_url: Automatic flow URL
            
        Returns:
            Authorization code
        """
        import asyncio
        
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        self._manual_auth_code_resolver = lambda code: future.set_result(code)
        
        async def wait_for_listener() -> str:
            if self._auth_code_listener:
                return await self._auth_code_listener.wait_for_authorization(
                    state,
                    lambda: None,  # on_ready - handled below
                )
            raise Exception("Auth code listener not initialized")
        
        async def handle_auth_urls() -> None:
            try:
                if skip_browser_open:
                    await auth_url_handler(manual_flow_url, automatic_flow_url)
                else:
                    await auth_url_handler(manual_flow_url)
                    # In a real implementation, we'd open the browser here
            except Exception as e:
                if not future.done():
                    future.set_exception(e)
        
        # Schedule URL handler
        asyncio.create_task(handle_auth_urls())
        
        # Wait for either manual input or listener callback
        try:
            result = await future
            if result is None:
                raise Exception("Authorization failed")
            return result
        except Exception:
            # Fall back to listener
            return await wait_for_listener()
    
    def handle_manual_auth_code_input(
        self,
        authorization_code: str,
        state: str,
    ) -> None:
        """
        Handle manual auth code input from user.
        
        Args:
            authorization_code: The authorization code
            state: State parameter
        """
        if self._manual_auth_code_resolver:
            self._manual_auth_code_resolver(authorization_code)
            self._manual_auth_code_resolver = None
            if self._auth_code_listener:
                self._auth_code_listener.close()
    
    def _format_tokens(
        self,
        response: OAuthTokenExchangeResponse,
        subscription_type: Optional[SubscriptionType],
        rate_limit_tier: Optional[RateLimitTier],
        profile: Optional[Dict[str, Any]],
    ) -> OAuthTokens:
        """Format token exchange response into OAuthTokens."""
        return OAuthTokens(
            access_token=response.access_token,
            refresh_token=response.refresh_token,
            expires_at=time.time() * 1000 + response.expires_in * 1000,
            scopes=parse_scopes(response.scope),
            subscription_type=subscription_type,
            rate_limit_tier=rate_limit_tier,
            profile=profile,
            token_account=response.account if response.account else None,
        )
    
    def cleanup(self) -> None:
        """Clean up any resources (like the local server)."""
        if self._auth_code_listener:
            self._auth_code_listener.close()
        self._manual_auth_code_resolver = None


# =============================================================================
# Global OAuth Service Instance
# =============================================================================

_oauth_service: Optional[OAuthService] = None


def get_oauth_service() -> OAuthService:
    """Get the global OAuth service instance."""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = OAuthService()
    return _oauth_service


# =============================================================================
# Legacy API Compatibility
# =============================================================================

class OAuthProvider(BaseModel):
    """OAuth provider configuration."""
    name: str
    client_id: str
    auth_url: str
    token_url: str
    scopes: List[str]


@dataclass
class OAuthToken:
    """Legacy OAuth token class."""
    access_token: str
    refresh_token: Optional[str]
    expires_at: float
    token_type: str


class OAuthServiceLegacy:
    """Legacy OAuth service for backward compatibility."""
    
    _providers: Dict[str, OAuthProvider] = {}
    _tokens: Dict[str, OAuthToken] = {}
    
    @classmethod
    def register_provider(
        cls,
        name: str,
        client_id: str,
        auth_url: str,
        token_url: str,
        scopes: Optional[List[str]] = None,
    ) -> None:
        cls._providers[name] = OAuthProvider(
            name=name,
            client_id=client_id,
            auth_url=auth_url,
            token_url=token_url,
            scopes=scopes or ["read:user"],
        )
    
    @classmethod
    def get_provider(cls, name: str) -> Optional[OAuthProvider]:
        return cls._providers.get(name)
    
    @classmethod
    async def initiate_auth(cls, provider_name: str) -> Optional[str]:
        provider = cls._providers.get(provider_name)
        if not provider:
            return None
        
        state = f"state_{time.time()}"
        auth_url = f"{provider.auth_url}?client_id={provider.client_id}&scope={' '.join(provider.scopes)}&state={state}"
        return auth_url
    
    @classmethod
    async def exchange_code(
        cls,
        provider_name: str,
        code: str,
    ) -> Optional[OAuthToken]:
        provider = cls._providers.get(provider_name)
        if not provider:
            return None
        
        token = OAuthToken(
            access_token=f"token_{code}_{time.time()}",
            refresh_token=None,
            expires_at=time.time() + 3600,
            token_type="Bearer",
        )
        cls._tokens[provider_name] = token
        return token
    
    @classmethod
    def get_token(cls, provider_name: str) -> Optional[OAuthToken]:
        token = cls._tokens.get(provider_name)
        if token and token.expires_at < time.time():
            return None
        return token
    
    @classmethod
    def is_authenticated(cls, provider_name: str) -> bool:
        return cls.get_token(provider_name) is not None
    
    @classmethod
    async def refresh_token(cls, provider_name: str) -> bool:
        token = cls._tokens.get(provider_name)
        if token and token.refresh_token:
            token.access_token = f"refreshed_{time.time()}"
            token.expires_at = time.time() + 3600
            return True
        return False
    
    @classmethod
    def logout(cls, provider_name: str) -> None:
        if provider_name in cls._tokens:
            del cls._tokens[provider_name]


# Alias for backward compatibility
OAuthService = OAuthServiceLegacy