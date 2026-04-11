"""OAuth service handling the OAuth 2.0 authorization code flow with PKCE."""

import asyncio
from typing import Callable, Optional

from .auth_code_listener import AuthCodeListener
from . import client as oauth_client
from . import crypto as oauth_crypto
from .types import OAuthTokens, RateLimitTier, SubscriptionType, OAuthProfileResponse


class OAuthService:
    """
    OAuth service that handles the OAuth 2.0 authorization code flow with PKCE.
    
    Supports two ways to get authorization codes:
    1. Automatic: Opens browser, redirects to localhost where we capture the code
    2. Manual: User manually copies and pastes the code (used in non-browser environments)
    """

    def __init__(self):
        self.code_verifier: str = oauth_crypto.generate_code_verifier()
        self.auth_code_listener: Optional[AuthCodeListener] = None
        self.port: Optional[int] = None
        self.manual_auth_code_resolver: Optional[Callable[[str], None]] = None

    async def start_oauth_flow(
        self,
        auth_url_handler: Callable[[str, Optional[str]], None],
        options: Optional[dict] = None,
    ) -> OAuthTokens:
        """
        Start OAuth flow and return tokens.
        
        Args:
            auth_url_handler: Async function that receives (manualFlowUrl, automaticFlowUrl)
                Called with both URLs when skipBrowserOpen is true, otherwise just manualFlowUrl
            options: Optional parameters:
                - login_with_claude_ai: bool - Use Claude.ai authorization
                - inference_only: bool - Request only inference scope
                - expires_in: int - Token expiration time
                - org_uuid: str - Organization UUID to pre-select
                - login_hint: str - Email to pre-populate
                - login_method: str - Specific login method
                - skip_browser_open: bool - Don't open browser, caller handles URLs
        
        Returns:
            OAuthTokens with access token, refresh token, and profile info
        """
        options = options or {}
        
        self.auth_code_listener = AuthCodeListener()
        self.port = await self.auth_code_listener.start()
        
        code_challenge = oauth_crypto.generate_code_challenge(self.code_verifier)
        state = oauth_crypto.generate_state()
        
        opts = {
            "code_challenge": code_challenge,
            "state": state,
            "port": self.port,
            "login_with_claude_ai": options.get("login_with_claude_ai"),
            "inference_only": options.get("inference_only"),
            "org_uuid": options.get("org_uuid"),
            "login_hint": options.get("login_hint"),
            "login_method": options.get("login_method"),
        }
        
        manual_flow_url = oauth_client.build_auth_url(**opts, is_manual=True)
        automatic_flow_url = oauth_client.build_auth_url(**opts, is_manual=False)
        
        authorization_code = await self.wait_for_authorization_code(
            state,
            lambda: auth_url_handler(manual_flow_url, automatic_flow_url if not options.get("skip_browser_open") else None),
        )
        
        is_automatic_flow = self.auth_code_listener.has_pending_response()
        
        use_manual_redirect = not is_automatic_flow
        
        try:
            token_response = await oauth_client.exchange_code_for_tokens(
                authorization_code,
                state,
                self.code_verifier,
                self.port,
                use_manual_redirect,
                options.get("expires_in"),
            )
            
            profile_info = await oauth_client.fetch_profile_info(
                token_response.access_token,
            )
            
            if is_automatic_flow:
                scopes = oauth_client.parse_scopes(token_response.scope)
                self.auth_code_listener.handle_success_redirect(scopes)
            
            return self.format_tokens(
                token_response,
                profile_info.get("subscription_type"),
                profile_info.get("rate_limit_tier"),
                profile_info.get("raw_profile"),
            )
        except Exception as e:
            if is_automatic_flow:
                self.auth_code_listener.handle_error_redirect()
            raise e
        finally:
            if self.auth_code_listener:
                self.auth_code_listener.close()

    async def wait_for_authorization_code(
        self,
        state: str,
        on_ready: Callable[[], None],
    ) -> str:
        """
        Wait for authorization code from either automatic or manual flow.
        
        Args:
            state: State parameter for CSRF protection
            on_ready: Callback when server is ready and flow can begin
            
        Returns:
            The authorization code
        """
        future = asyncio.Future()
        self.manual_auth_code_resolver = lambda code: future.set_result(code)
        
        if self.auth_code_listener:
            try:
                authorization_code = await self.auth_code_listener.wait_for_authorization(
                    state,
                    on_ready,
                )
                self.manual_auth_code_resolver = None
                return authorization_code
            except Exception as e:
                self.manual_auth_code_resolver = None
                raise e
        else:
            self.manual_auth_code_resolver = None
            raise Exception("Auth code listener not initialized")

    def handle_manual_auth_code_input(
        self,
        authorization_code: str,
        state: str,
    ) -> None:
        """
        Handle manual flow callback when user pastes the auth code.
        
        Args:
            authorization_code: The pasted authorization code
            state: The state parameter for verification
        """
        if self.manual_auth_code_resolver:
            self.manual_auth_code_resolver(authorization_code)
            self.manual_auth_code_resolver = None
            if self.auth_code_listener:
                self.auth_code_listener.close()

    def format_tokens(
        self,
        response: oauth_client.OAuthTokenExchangeResponse,
        subscription_type: SubscriptionType | None,
        rate_limit_tier: RateLimitTier | None,
        profile: OAuthProfileResponse | None,
    ) -> OAuthTokens:
        """
        Format token exchange response into final OAuthTokens structure.
        
        Args:
            response: Token exchange response
            subscription_type: Subscription type from profile
            rate_limit_tier: Rate limit tier from profile
            profile: Raw profile response
            
        Returns:
            Formatted OAuthTokens
        """
        import time
        
        token_account = None
        if response.account:
            token_account = oauth_client.OAuthAccountInfo(
                uuid=response.account.uuid,
                email_address=response.account.email_address,
                organization_uuid=response.organization.uuid if response.organization else None,
            )
        
        return OAuthTokens(
            access_token=response.access_token,
            refresh_token=response.refresh_token,
            expires_at=time.time() * 1000 + response.expires_in * 1000,
            token_type="Bearer",
            scopes=oauth_client.parse_scopes(response.scope),
            subscription_type=subscription_type,
            rate_limit_tier=rate_limit_tier,
            profile=profile,
            token_account=token_account,
        )

    def cleanup(self) -> None:
        """Clean up any resources (like the local server)."""
        if self.auth_code_listener:
            self.auth_code_listener.close()
        self.manual_auth_code_resolver = None
