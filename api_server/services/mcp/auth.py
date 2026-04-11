"""Authentication handling for MCP service."""

import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


AUTH_REQUEST_TIMEOUT_MS = 30000
MAX_LOCK_RETRIES = 5
MAX_REFRESH_ATTEMPTS = 3
PROACTIVE_REFRESH_THRESHOLD_SECONDS = 300

NONSTANDARD_INVALID_GRANT_ALIASES = {
    "invalid_refresh_token",
    "expired_refresh_token",
    "token_expired",
}

SENSITIVE_OAUTH_PARAMS = [
    "state",
    "nonce",
    "code_challenge",
    "code_verifier",
    "code",
]


class MCPRefreshFailureReason:
    METADATA_DISCOVERY_FAILED = "metadata_discovery_failed"
    NO_CLIENT_INFO = "no_client_info"
    NO_TOKENS_RETURNED = "no_tokens_returned"
    INVALID_GRANT = "invalid_grant"
    TRANSIENT_RETRIES_EXHAUSTED = "transient_retries_exhausted"
    REQUEST_FAILED = "request_failed"


class MCPOAuthFlowErrorReason:
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    PROVIDER_DENIED = "provider_denied"
    STATE_MISMATCH = "state_mismatch"
    PORT_UNAVAILABLE = "port_unavailable"
    SDK_AUTH_FAILED = "sdk_auth_failed"
    TOKEN_EXCHANGE_FAILED = "token_exchange_failed"
    UNKNOWN = "unknown"


def redact_sensitive_url_params(url: str) -> str:
    """
    Redacts sensitive OAuth query parameters from a URL for safe logging.
    """
    try:
        from urllib.parse import urlparse, parse_qs, urlencode as uencode
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        for param in SENSITIVE_OAUTH_PARAMS:
            if param in params:
                params[param] = ["[REDACTED]"]
        
        new_query = uencode(params, doseq=True)
        return parsed._replace(query=new_query).geturl()
    except Exception:
        return url


def normalize_oauth_error_body(response: Any) -> Any:
    if hasattr(response, "ok") and response.ok:
        return response
    return response


async def create_auth_fetch() -> Callable:
    import aiohttp
    
    async def auth_fetch(url: str, init: Optional[Dict[str, Any]] = None) -> Any:
        timeout = aiohttp.ClientTimeout(total=AUTH_REQUEST_TIMEOUT_MS / 1000)
        
        method = init.get("method", "GET") if init else "GET"
        headers = init.get("headers", {}) if init else {}
        body = init.get("body") if init else None
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, headers=headers, data=body) as response:
                if not response.ok:
                    return response
                
                try:
                    text = await response.text()
                    parsed = json.loads(text) if text else {}
                    
                    if "error" in parsed and "access_token" not in parsed:
                        error = parsed.get("error", "")
                        if error in NONSTANDARD_INVALID_GRANT_ALIASES:
                            parsed["error"] = "invalid_grant"
                            parsed["error_description"] = parsed.get(
                                "error_description", 
                                f"Server returned non-standard error code: {error}"
                            )
                        
                        return MockResponse(
                            status=400,
                            headers=response.headers,
                            json_data=parsed
                        )
                    
                    return MockResponse(
                        status=response.status,
                        headers=response.headers,
                        json_data=parsed
                    )
                except Exception:
                    return response
        
    return auth_fetch


class MockResponse:
    def __init__(self, status: int, headers: Dict[str, str], json_data: Optional[Dict] = None):
        self.status = status
        self.ok = 200 <= status < 300
        self._headers = headers
        self._json_data = json_data
    
    @property
    def headers(self) -> Dict[str, str]:
        return self._headers
    
    async def json(self) -> Dict[str, Any]:
        return self._json_data or {}
    
    async def text(self) -> str:
        return json.dumps(self._json_data) if self._json_data else ""


async def fetch_auth_server_metadata(
    server_name: str,
    server_url: str,
    configured_metadata_url: Optional[str] = None,
    fetch_fn: Optional[Callable] = None,
) -> Optional[Dict[str, Any]]:
    if configured_metadata_url:
        if not configured_metadata_url.startswith("https://"):
            raise ValueError(
                f"authServerMetadataUrl must use https:// (got: {configured_metadata_url})"
            )
        
        fetch = fetch_fn or await create_auth_fetch()
        response = await fetch(configured_metadata_url, {
            "headers": {"Accept": "application/json"}
        })
        
        if response.ok:
            return await response.json()
        
        raise Exception(
            f"HTTP {response.status} fetching configured auth server metadata from {configured_metadata_url}"
        )
    
    # TODO: Implement RFC 9728 → RFC 8414 discovery via SDK equivalent
    # For now, return None to indicate discovery failed
    logger.debug(f"RFC 9728 discovery not implemented for {server_name}")
    return None


def get_server_key(
    server_name: str,
    server_config: Dict[str, Any],
) -> str:
    config_json = json.dumps({
        "type": server_config.get("type"),
        "url": server_config.get("url"),
        "headers": server_config.get("headers") or {},
    }, sort_keys=True)

    hash_digest = hashlib.sha256(config_json.encode()).hexdigest()[:16]
    return f"{server_name}|{hash_digest}"


def has_mcp_discovery_but_no_token(
    server_name: str,
    server_config: Dict[str, Any],
    storage_data: Optional[Dict[str, Any]] = None,
) -> bool:
    if storage_data is None:
        return False

    server_key = get_server_key(server_name, server_config)
    entry = storage_data.get("mcp_oauth", {}).get(server_key)

    if entry is None:
        return False

    has_xaa = server_config.get("oauth", {}).get("xaa", False)
    if has_xaa:
        return False

    return bool(entry) and not entry.get("access_token") and not entry.get("refresh_token")


@dataclass
class MCPOAuthTokens:
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int = 0
    scope: Optional[str] = None
    token_type: str = "Bearer"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


@dataclass
class MCPOAuthClientInfo:
    client_id: str
    client_secret: Optional[str] = None


class AuthenticationCancelledError(Exception):
    pass


class MCPAuthProvider:
    def __init__(
        self,
        server_name: str,
        server_config: Dict[str, Any],
        redirect_uri: Optional[str] = None,
        handle_redirection: bool = True,
        on_authorization_url: Optional[Callable[[str], None]] = None,
        skip_browser_open: bool = False,
    ):
        self.server_name = server_name
        self.server_config = server_config
        self.redirect_uri = redirect_uri
        self.handle_redirection = handle_redirection
        self.on_authorization_url_callback = on_authorization_url
        self.skip_browser_open = skip_browser_open

        self._state: Optional[str] = None
        self._scopes: Optional[str] = None
        self._metadata: Optional[Dict[str, Any]] = None
        self._code_verifier: Optional[str] = None
        self._authorization_url: Optional[str] = None
        self._pending_step_up_scope: Optional[str] = None
        self._refresh_in_progress: Optional[Any] = None

    async def state(self) -> str:
        if not self._state:
            import secrets
            self._state = secrets.token_urlsafe(32)
        return self._state

    async def client_information(self) -> Optional[MCPOAuthClientInfo]:
        storage = _get_secure_storage()
        data = storage.read()
        server_key = get_server_key(self.server_name, self.server_config)

        stored_info = data.get("mcp_oauth", {}).get(server_key, {})
        client_id = stored_info.get("client_id")

        if client_id:
            return MCPOAuthClientInfo(
                client_id=client_id,
                client_secret=stored_info.get("client_secret"),
            )

        config_client_id = self.server_config.get("oauth", {}).get("client_id")
        if config_client_id:
            client_config = data.get("mcp_oauth_client_config", {}).get(server_key, {})
            return MCPOAuthClientInfo(
                client_id=config_client_id,
                client_secret=client_config.get("client_secret"),
            )

        return None

    async def save_client_information(
        self,
        client_info: MCPOAuthClientInfo,
    ) -> None:
        storage = _get_secure_storage()
        existing_data = storage.read() or {}
        server_key = get_server_key(self.server_name, self.server_config)

        existing_entry = existing_data.get("mcp_oauth", {}).get(server_key, {})

        updated_data = {
            **existing_data,
            "mcp_oauth": {
                **existing_data.get("mcp_oauth", {}),
                server_key: {
                    **existing_entry,
                    "server_name": self.server_name,
                    "server_url": self.server_config.get("url"),
                    "client_id": client_info.client_id,
                    "client_secret": client_info.client_secret,
                    "access_token": existing_entry.get("access_token") or "",
                    "expires_at": existing_entry.get("expires_at") or 0,
                },
            },
        }

        storage.update(updated_data)

    async def code_verifier(self) -> str:
        if not self._code_verifier:
            import secrets
            self._code_verifier = secrets.token_urlsafe(64)
        return self._code_verifier

    async def save_code_verifier(self, code_verifier: str) -> None:
        self._code_verifier = code_verifier

    async def invalidate_credentials(
        self,
        scope: str = "all",
    ) -> None:
        storage = _get_secure_storage()
        existing_data = storage.read()
        if not existing_data:
            return

        server_key = get_server_key(self.server_name, self.server_config)
        token_data = existing_data.get("mcp_oauth", {}).get(server_key)
        if not token_data:
            return

        if scope == "all":
            if "mcp_oauth" in existing_data and server_key in existing_data["mcp_oauth"]:
                del existing_data["mcp_oauth"][server_key]
        elif scope == "tokens":
            token_data["access_token"] = ""
            token_data["refresh_token"] = None
            token_data["expires_at"] = 0
        elif scope == "client":
            token_data["client_id"] = None
            token_data["client_secret"] = None
        elif scope == "verifier":
            self._code_verifier = None
            return
        elif scope == "discovery":
            token_data["discovery_state"] = None
            token_data["step_up_scope"] = None

        storage.update(existing_data)

    def mark_step_up_pending(self, scope: str) -> None:
        self._pending_step_up_scope = scope
        logger.debug(f"Marked step-up pending for {self.server_name}: {scope}")

    @property
    def client_metadata(self) -> Dict[str, Any]:
        metadata_dict = {
            "client_name": f"Claude Code ({self.server_name})",
            "redirect_uris": [self.redirect_uri] if self.redirect_uri else [],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }
        
        # Include scope from metadata if available
        metadata_scope = get_scope_from_metadata(self._metadata)
        if metadata_scope:
            metadata_dict["scope"] = metadata_scope
            logger.debug(f"{self.server_name}: Using scope from metadata: {metadata_scope}")
        
        return metadata_dict

    @property
    def redirect_url(self) -> str:
        return self.redirect_uri or ""

    @property
    def authorization_url(self) -> Optional[str]:
        return self._authorization_url

    @property
    def client_metadata_url(self) -> Optional[str]:
        override = os.environ.get("MCP_OAUTH_CLIENT_METADATA_URL")
        if override:
            logger.debug(f"{self.server_name}: Using CIMD URL from env: {override}")
            return override
        return "https://claude.ai/oauth/claude-code-client-metadata"

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        self._metadata = metadata

    async def save_tokens(self, tokens: MCPOAuthTokens) -> None:
        self._pending_step_up_scope = None
        storage = _get_secure_storage()
        existing_data = storage.read() or {}
        server_key = get_server_key(self.server_name, self.server_config)

        updated_data = {
            **existing_data,
            "mcp_oauth": {
                **existing_data.get("mcp_oauth", {}),
                server_key: {
                    **existing_data.get("mcp_oauth", {}).get(server_key, {}),
                    "server_name": self.server_name,
                    "server_url": self.server_config.get("url"),
                    "access_token": tokens.access_token,
                    "refresh_token": tokens.refresh_token,
                    "expires_at": int(time.time() * 1000) + (tokens.expires_in or 3600) * 1000,
                    "scope": tokens.scope,
                },
            },
        }

        storage.update(updated_data)

    async def tokens(self) -> Optional[MCPOAuthTokens]:
        storage = _get_secure_storage()
        data = storage.read()
        server_key = get_server_key(self.server_name, self.server_config)

        token_data = data.get("mcp_oauth", {}).get(server_key) if data else None

        # XAA flow: silent refresh using cached id_token
        if (
            _is_xaa_enabled() and
            self.server_config.get("oauth", {}).get("xaa") and
            (not token_data or not token_data.get("refresh_token")) and
            (not token_data or not token_data.get("access_token") or
                (token_data.get("expires_at", 0) - int(time.time() * 1000)) / 1000 <= 300)
        ):
            if not self._refresh_in_progress:
                logger.debug(f"{self.server_name}: XAA: attempting silent exchange")
                self._refresh_in_progress = self.xaa_refresh()
            try:
                refreshed = await self._refresh_in_progress
                if refreshed:
                    return refreshed
            except Exception as e:
                logger.debug(f"{self.server_name}: XAA silent exchange failed: {e}")
            self._refresh_in_progress = None

        if not token_data:
            logger.debug(f"No token data found for {self.server_name}")
            return None

        expires_in = (token_data.get("expires_at", 0) - int(time.time() * 1000)) / 1000

        if expires_in <= 0 and not token_data.get("refresh_token"):
            return None

        current_scopes = token_data.get("scope", "").split(" ") if token_data.get("scope") else []
        needs_step_up = False
        if self._pending_step_up_scope:
            needed_scopes = self._pending_step_up_scope.split(" ")
            needs_step_up = any(s not in current_scopes for s in needed_scopes)

        if expires_in <= 300 and token_data.get("refresh_token") and not needs_step_up:
            if not self._refresh_in_progress:
                self._refresh_in_progress = self.refresh_authorization(
                    token_data.get("refresh_token", "")
                )
            try:
                refreshed = await self._refresh_in_progress
                if refreshed:
                    logger.debug("Token refreshed successfully")
                    return refreshed
            except Exception as e:
                logger.debug(f"Token refresh error: {e}")

        return MCPOAuthTokens(
            access_token=token_data.get("access_token", ""),
            refresh_token=None if needs_step_up else token_data.get("refresh_token"),
            expires_in=int(expires_in),
            scope=token_data.get("scope"),
            token_type="Bearer",
        )

    async def refresh_authorization(
        self,
        refresh_token: str,
    ) -> Optional[MCPOAuthTokens]:
        import asyncio
        import filelock

        server_key = get_server_key(self.server_name, self.server_config)
        claude_dir = os.environ.get("CLAUDE_CONFIG_DIR", "/tmp")
        lockfile_path = os.path.join(claude_dir, f"mcp-refresh-{server_key}.lock")

        lock = filelock.FileLock(lockfile_path, timeout=1)
        acquired = False
        for retry in range(MAX_LOCK_RETRIES):
            try:
                acquired = lock.acquire(timeout=1)
                if acquired:
                    break
            except filelock.LockException:
                await asyncio.sleep(1 + retry)
                continue

        try:
            storage = _get_secure_storage()
            data = storage.read()
            token_data = data.get("mcp_oauth", {}).get(server_key, {}) if data else {}

            expires_in = (token_data.get("expires_at", 0) - int(time.time() * 1000)) / 1000
            if expires_in > 300:
                return MCPOAuthTokens(
                    access_token=token_data.get("access_token", ""),
                    refresh_token=token_data.get("refresh_token"),
                    expires_in=int(expires_in),
                    scope=token_data.get("scope"),
                )

            return await self._do_refresh(refresh_token)
        finally:
            if acquired:
                try:
                    lock.release()
                except Exception:
                    pass

    async def _do_refresh(self, refresh_token: str) -> Optional[MCPOAuthTokens]:
        for attempt in range(MAX_REFRESH_ATTEMPTS):
            try:
                auth_fetch = await create_auth_fetch()
                metadata = self._metadata

                if not metadata:
                    cached = await self.discovery_state()
                    if cached and cached.get("authorization_server_metadata"):
                        metadata = cached.get("authorization_server_metadata")

                if not metadata:
                    metadata = await fetch_auth_server_metadata(
                        self.server_name,
                        self.server_config.get("url", ""),
                        self.server_config.get("oauth", {}).get("auth_server_metadata_url"),
                        auth_fetch,
                    )

                if not metadata:
                    logger.debug("Failed to discover OAuth metadata")
                    return None

                self._metadata = metadata

                client_info = await self.client_information()
                if not client_info:
                    logger.debug("No client information available")
                    return None

                result = await self._execute_token_refresh(
                    metadata, client_info, refresh_token, auth_fetch
                )
                if result:
                    await self.save_tokens(result)
                    return result

            except Exception as e:
                error_msg = str(e)
                is_invalid_grant = "invalid_grant" in error_msg.lower()
                is_retryable = any(x in error_msg.lower() for x in ["timeout", "temporarily", "too many"])

                if is_invalid_grant:
                    await self.invalidate_credentials("tokens")
                    return None

                if is_retryable and attempt < MAX_REFRESH_ATTEMPTS - 1:
                    delay_ms = 1000 * (2 ** attempt)
                    await asyncio.sleep(delay_ms / 1000)
                    continue

                return None

        return None

    async def _execute_token_refresh(
        self,
        metadata: Dict[str, Any],
        client_info: MCPOAuthClientInfo,
        refresh_token: str,
        auth_fetch: Callable,
    ) -> Optional[MCPOAuthTokens]:
        import aiohttp

        token_endpoint = metadata.get("token_endpoint")
        if not token_endpoint:
            return None

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        if client_info.client_id:
            data["client_id"] = client_info.client_id

        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_endpoint,
                data=data,
                headers=headers,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "error" not in result:
                        return MCPOAuthTokens(
                            access_token=result.get("access_token", ""),
                            refresh_token=result.get("refresh_token"),
                            expires_at=int(time.time() * 1000) + (result.get("expires_in", 3600) * 1000),
                            scope=result.get("scope"),
                            token_type=result.get("token_type", "Bearer"),
                        )
                elif response.status == 400:
                    result = await response.json()
                    if result.get("error") == "invalid_grant":
                        raise Exception("invalid_grant")

        return None

    async def discovery_state(self) -> Optional[Dict[str, Any]]:
        storage = _get_secure_storage()
        data = storage.read()
        server_key = get_server_key(self.server_name, self.server_config)

        cached = data.get("mcp_oauth", {}).get(server_key, {}).get("discovery_state") if data else None
        if cached and cached.get("authorization_server_url"):
            logger.debug(f"{self.server_name}: Returning cached discovery state (authServer: {cached.get('authorization_server_url')})")
            return cached

        metadata_url = self.server_config.get("oauth", {}).get("auth_server_metadata_url")
        if metadata_url:
            try:
                auth_fetch = await create_auth_fetch()
                metadata = await fetch_auth_server_metadata(
                    self.server_name,
                    self.server_config.get("url", ""),
                    metadata_url,
                    auth_fetch,
                )
                if metadata:
                    return {
                        "authorization_server_url": metadata.get("issuer", ""),
                        "authorization_server_metadata": metadata,
                    }
            except Exception as e:
                logger.debug(f"Failed to fetch from configured metadata URL: {e}")

        return None

    async def save_discovery_state(self, state: Dict[str, Any]) -> None:
        storage = _get_secure_storage()
        existing_data = storage.read() or {}
        server_key = get_server_key(self.server_name, self.server_config)

        existing_entry = existing_data.get("mcp_oauth", {}).get(server_key, {})

        logger.debug(f"{self.server_name}: Saving discovery state (authServer: {state.get('authorization_server_url', '')})")

        updated_data = {
            **existing_data,
            "mcp_oauth": {
                **existing_data.get("mcp_oauth", {}),
                server_key: {
                    **existing_entry,
                    "server_name": self.server_name,
                    "server_url": self.server_config.get("url"),
                    "access_token": existing_entry.get("access_token", ""),
                    "expires_at": existing_entry.get("expires_at", 0),
                    "discovery_state": {
                        "authorization_server_url": state.get("authorization_server_url", ""),
                        "resource_metadata_url": state.get("resource_metadata_url"),
                    },
                },
            },
        }

        storage.update(updated_data)

    async def redirect_to_authorization(self, authorization_url: Any) -> None:
        # Handle both string and URL objects
        if hasattr(authorization_url, 'to_string'):
            url_str = authorization_url.to_string()
        elif hasattr(authorization_url, 'geturl'):
            url_str = authorization_url.geturl()
        else:
            url_str = str(authorization_url)
        
        self._authorization_url = url_str
        
        # Extract scopes from URL for step-up auth
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url_str)
            scopes = parse_qs(parsed.query).get('scope', [None])[0]
            if scopes:
                self._scopes = scopes
                logger.debug(f"{self.server_name}: Captured scopes from authorization URL: {scopes}")
            else:
                metadata_scope = get_scope_from_metadata(self._metadata)
                if metadata_scope:
                    self._scopes = metadata_scope
                    logger.debug(f"{self.server_name}: Using scopes from metadata: {metadata_scope}")
                else:
                    logger.debug(f"{self.server_name}: No scopes available from URL or metadata")
        except Exception:
            pass
        
        # Persist scope for step-up auth when handleRedirection=false
        if self._scopes and not self.handle_redirection:
            storage = _get_secure_storage()
            existing_data = storage.read() or {}
            server_key = get_server_key(self.server_name, self.server_config)
            existing = existing_data.get("mcp_oauth", {}).get(server_key)
            if existing:
                existing["step_up_scope"] = self._scopes
                storage.update(existing_data)
                logger.debug(f"{self.server_name}: Persisted step-up scope: {self._scopes}")
        
        if not self.handle_redirection:
            logger.debug(f"Redirection handling disabled for {self.server_name}")
            return
        
        logger.debug(f"Redirecting to authorization URL: {redact_sensitive_url_params(url_str)}")
        
        if self.on_authorization_url_callback:
            self.on_authorization_url_callback(url_str)
        
        if not self.skip_browser_open:
            import webbrowser
            try:
                webbrowser.open(url_str)
            except Exception as e:
                logger.warning(f"Failed to open browser: {e}")

    async def xaa_refresh(self) -> Optional[MCPOAuthTokens]:
        """XAA silent refresh: cached id_token → exchange → new access_token."""
        idp_settings = _get_xaa_idp_settings()
        if not idp_settings:
            return None
        
        id_token = _get_cached_idp_id_token(idp_settings.get("issuer", ""))
        if not id_token:
            logger.debug(f"{self.server_name}: XAA: id_token not cached")
            return None
        
        client_id = self.server_config.get("oauth", {}).get("client_id")
        client_config = _get_mcp_client_config(self.server_name, self.server_config)
        if not client_id or not client_config:
            return None
        
        idp_client_secret = _get_idp_client_secret(idp_settings.get("issuer", ""))
        
        try:
            oidc = await _discover_oidc(idp_settings["issuer"])
            tokens = await _perform_cross_app_access(
                server_url=self.server_config["url"],
                client_id=client_id,
                client_secret=client_config.get("client_secret", ""),
                idp_client_id=idp_settings["client_id"],
                idp_client_secret=idp_client_secret,
                idp_id_token=id_token,
                idp_token_endpoint=oidc["token_endpoint"],
                server_name=self.server_name,
                abort_signal=None,
            )
            
            storage = _get_secure_storage()
            existing_data = storage.read() or {}
            server_key = get_server_key(self.server_name, self.server_config)
            prev = existing_data.get("mcp_oauth", {}).get(server_key, {})
            
            storage.update({
                **existing_data,
                "mcp_oauth": {
                    **existing_data.get("mcp_oauth", {}),
                    server_key: {
                        **prev,
                        "server_name": self.server_name,
                        "server_url": self.server_config["url"],
                        "access_token": tokens.get("access_token", ""),
                        "refresh_token": tokens.get("refresh_token") or prev.get("refresh_token"),
                        "expires_at": int(time.time() * 1000) + (tokens.get("expires_in", 3600) * 1000),
                        "scope": tokens.get("scope"),
                        "client_id": client_id,
                        "client_secret": client_config.get("client_secret"),
                        "discovery_state": {
                            "authorization_server_url": tokens.get("authorization_server_url", ""),
                        },
                    },
                },
            })
            
            return MCPOAuthTokens(
                access_token=tokens.get("access_token", ""),
                refresh_token=tokens.get("refresh_token"),
                expires_in=tokens.get("expires_in", 3600),
                scope=tokens.get("scope"),
            )
        except Exception as e:
            logger.debug(f"{self.server_name}: XAA refresh failed: {e}")
            if isinstance(e, XaaTokenExchangeError) and e.should_clear_id_token:
                _clear_idp_id_token(idp_settings.get("issuer", ""))
            return None


class SecureStorage:
    """
    Secure storage for OAuth tokens.
    Uses file-based storage with optional keyring integration.
    """

    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0
        self._cache_ttl: float = 60.0

    def _get_storage_path(self) -> Optional[str]:
        return os.environ.get("MCP_SECURE_STORAGE_PATH")

    def _invalidate_cache(self) -> None:
        self._cache = None
        self._cache_time = 0

    def read(self) -> Optional[Dict[str, Any]]:
        current_time = time.time()
        if self._cache and (current_time - self._cache_time) < self._cache_ttl:
            return self._cache

        storage_path = self._get_storage_path()
        if not storage_path:
            return self._read_from_keyring()

        try:
            if os.path.exists(storage_path):
                with open(storage_path, "r") as f:
                    self._cache = json.load(f)
                    self._cache_time = current_time
                    return self._cache
        except Exception as e:
            logger.warning(f"Failed to read secure storage: {e}")

        return self._read_from_keyring()

    def _read_from_keyring(self) -> Optional[Dict[str, Any]]:
        try:
            import keyring
            data = keyring.get_password("mcp_oauth", "storage_data")
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    def update(self, data: Dict[str, Any]) -> None:
        storage_path = self._get_storage_path()
        
        if storage_path:
            try:
                os.makedirs(os.path.dirname(storage_path), exist_ok=True)
                with open(storage_path, "w") as f:
                    json.dump(data, f)
                self._cache = data
                self._cache_time = time.time()
            except Exception as e:
                logger.error(f"Failed to update secure storage: {e}")
                self._update_keyring(data)
        else:
            self._update_keyring(data)

    def _update_keyring(self, data: Dict[str, Any]) -> None:
        try:
            import keyring
            keyring.set_password("mcp_oauth", "storage_data", json.dumps(data))
            self._cache = data
            self._cache_time = time.time()
        except Exception as e:
            logger.error(f"Failed to update keyring storage: {e}")

    def read_async(self) -> Optional[Dict[str, Any]]:
        return self.read()


_storage_instance: Optional[SecureStorage] = None


def _get_secure_storage() -> SecureStorage:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = SecureStorage()
    return _storage_instance


def get_auth_token(
    server_name: str,
    server_config: Dict[str, Any],
) -> Optional[str]:
    storage = _get_secure_storage()
    data = storage.read()
    if not data:
        return None

    server_key = get_server_key(server_name, server_config)
    token_data = data.get("mcp_oauth", {}).get(server_key)

    if not token_data:
        return None

    access_token = token_data.get("access_token")
    if not access_token:
        return None

    expires_at = token_data.get("expires_at", 0)
    if expires_at > 0:
        current_time = int(time.time() * 1000)
        if current_time >= expires_at:
            return None

    return access_token


def get_token_expiry(
    server_name: str,
    server_config: Dict[str, Any],
) -> Optional[int]:
    storage = _get_secure_storage()
    data = storage.read()
    if not data:
        return None
    
    server_key = get_server_key(server_name, server_config)
    token_data = data.get("mcp_oauth", {}).get(server_key)
    
    if not token_data:
        return None
    
    return token_data.get("expires_at")


def has_valid_token(
    server_name: str,
    server_config: Dict[str, Any],
) -> bool:
    token = get_auth_token(server_name, server_config)
    return token is not None


def get_token_scope(
    server_name: str,
    server_config: Dict[str, Any],
) -> Optional[str]:
    storage = _get_secure_storage()
    data = storage.read()
    if not data:
        return None
    
    server_key = get_server_key(server_name, server_config)
    token_data = data.get("mcp_oauth", {}).get(server_key)
    
    if not token_data:
        return None
    
    return token_data.get("scope")


async def refresh_auth_token(
    server_name: str,
    server_config: Dict[str, Any],
    refresh_token: str,
) -> Optional[MCPOAuthTokens]:
    provider = MCPAuthProvider(server_name, server_config)

    storage = _get_secure_storage()
    data = storage.read()
    server_key = get_server_key(server_name, server_config)
    token_data = data.get("mcp_oauth", {}).get(server_key, {})

    expires_in = (token_data.get("expires_at", 0) - int(time.time() * 1000)) / 1000
    if expires_in > 300:
        return MCPOAuthTokens(
            access_token=token_data.get("access_token", ""),
            refresh_token=token_data.get("refresh_token"),
            expires_at=token_data.get("expires_at", 0),
            scope=token_data.get("scope"),
        )

    new_tokens = await provider.refresh_authorization(refresh_token)
    return new_tokens


def invalidate_auth_token(
    server_name: str,
    server_config: Dict[str, Any],
) -> None:
    storage = _get_secure_storage()
    existing_data = storage.read()
    if not existing_data:
        return
    
    server_key = get_server_key(server_name, server_config)
    token_data = existing_data.get("mcp_oauth", {}).get(server_key)
    
    if not token_data:
        return
    
    token_data["access_token"] = ""
    token_data["refresh_token"] = None
    token_data["expires_at"] = 0
    
    storage.update(existing_data)


def get_oauth_client_id(
    server_name: str,
    server_config: Dict[str, Any],
) -> Optional[str]:
    storage = _get_secure_storage()
    data = storage.read()
    if not data:
        return None
    
    server_key = get_server_key(server_name, server_config)
    token_data = data.get("mcp_oauth", {}).get(server_key)
    
    if token_data:
        return token_data.get("client_id")
    
    return server_config.get("oauth", {}).get("client_id")


async def perform_mcp_oauth_flow(
    server_name: str,
    server_config: Dict[str, Any],
    on_authorization_url: Optional[Callable[[str], None]] = None,
    abort_signal: Optional[Any] = None,
    skip_browser_open: bool = False,
    callback_port: Optional[int] = None,
) -> None:
    """Complete OAuth flow for MCP server authentication."""
    from aiohttp import web
    
    provider = MCPAuthProvider(
        server_name,
        server_config,
        handle_redirection=True,
        on_authorization_url=on_authorization_url,
    )

    oauth_state = await provider.state()
    logger.info(f"Starting OAuth flow for {server_name}")
    logger.debug(f"Authorization state: {oauth_state}")

    # XAA flow
    if server_config.get("oauth", {}).get("xaa"):
        if not _is_xaa_enabled():
            raise Error(f"XAA is not enabled (set CLAUDE_CODE_ENABLE_XAA=1). Remove 'oauth.xaa' from server '{server_name}' to use the standard consent flow.")
        
        await perform_mcp_xaa_auth(
            server_name,
            server_config,
            on_authorization_url,
            abort_signal,
            skip_browser_open,
        )
        return

    # Standard OAuth flow with callback server
    auth_result = {"code": None, "error": None}
    
    async def create_callback_server(port: int):
        resolved = False
        
        def resolve_once(code: str = None, error: str = None):
            nonlocal resolved
            if resolved:
                return
            resolved = True
            auth_result["code"] = code
            auth_result["error"] = error
        
        async def handle_callback(request):
            nonlocal resolved
            
            code = request.query.get("code")
            state = request.query.get("state")
            error = request.query.get("error")
            error_description = request.query.get("error_description", "")
            
            if not error and state != oauth_state:
                logger.warning(f"OAuth state mismatch for {server_name}")
                resolve_once(error="state_mismatch")
                return web.Response(text="Invalid state parameter", status=400)
            
            if error:
                logger.warning(f"OAuth error for {server_name}: {error}")
                resolve_once(error=f"{error}: {error_description}")
                return web.Response(text=f"Error: {error}", status=200)
            
            if code:
                logger.info(f"Received authorization code for {server_name}")
                resolve_once(code=code)
                return web.Response(text="Authentication successful. You can close this window.", status=200)
            
            return web.Response(text="Waiting for authorization...", status=200)
        
        app = web.Application()
        app.router.add_get("/callback", handle_callback)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", port)
        await site.start()
        
        return runner, resolve_once
    
    if not callback_port:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            callback_port = s.getsockname()[1]
    
    try:
        runner, resolve_func = await create_callback_server(callback_port)
        
        try:
            auth_url = await provider.authorization_url()
            if on_authorization_url and auth_url:
                on_authorization_url(auth_url)
            
            timeout_seconds = 300
            start_time = time.time()
            
            while not auth_result["code"] and not auth_result["error"]:
                if abort_signal and getattr(abort_signal, "aborted", False):
                    raise AuthenticationCancelledError()
                
                if time.time() - start_time > timeout_seconds:
                    raise Error("Authentication timeout")
                
                await asyncio.sleep(0.1)
            
            if auth_result["error"]:
                if "state_mismatch" in auth_result["error"]:
                    raise Error("OAuth state mismatch - possible CSRF attack")
                raise Error(f"OAuth error: {auth_result['error']}")
            
            if not auth_result["code"]:
                raise Error("No authorization code received")
            
            logger.info("Authorization code received, completing flow")
            
        finally:
            await runner.cleanup()
    
    except Exception as e:
        logger.error(f"OAuth flow failed for {server_name}: {e}")
        raise


def _is_xaa_enabled() -> bool:
    """Check if XAA is enabled via environment variable."""
    return os.environ.get("CLAUDE_CODE_ENABLE_XAA", "").lower() in ("1", "true", "yes")


def clear_server_tokens_from_local_storage(
    server_name: str,
    server_config: Dict[str, Any],
) -> None:
    """Clear stored tokens for a server from local storage."""
    storage = _get_secure_storage()
    existing_data = storage.read()
    if not existing_data or not existing_data.get("mcp_oauth"):
        return

    server_key = get_server_key(server_name, server_config)
    if server_key in existing_data.get("mcp_oauth", {}):
        del existing_data["mcp_oauth"][server_key]
        storage.update(existing_data)
        logger.debug(f"Cleared stored tokens for {server_name}")


async def revoke_token(
    server_name: str,
    endpoint: str,
    token: str,
    token_type_hint: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    access_token: Optional[str] = None,
    auth_method: str = "client_secret_basic",
) -> None:
    """
    Revokes a single token on the OAuth server.
    
    Per RFC 7009, public clients should authenticate by including client_id
    in the request body, NOT via Authorization header.
    """
    import aiohttp
    
    params = {
        "token": token,
        "token_type_hint": token_type_hint,
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    # RFC 7009 §2.1 requires client auth per RFC 6749 §2.3
    if client_id and client_secret:
        if auth_method == "client_secret_post":
            params["client_id"] = client_id
            params["client_secret"] = client_secret
        else:
            import base64
            encoded = base64.b64encode(
                f"{client_id}:{client_secret}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {encoded}"
    elif client_id:
        params["client_id"] = client_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, data=params, headers=headers) as response:
                if response.status == 200:
                    logger.debug(f"Successfully revoked {token_type_hint}")
                elif response.status == 401 and access_token:
                    # Fallback for non-RFC-7009-compliant servers
                    logger.debug(f"Got 401, retrying {token_type_hint} revocation with Bearer auth")
                    params.pop("client_id", None)
                    params.pop("client_secret", None)
                    headers["Authorization"] = f"Bearer {access_token}"
                    async with session.post(endpoint, data=params, headers=headers) as retry_response:
                        if retry_response.status == 200:
                            logger.debug(f"Successfully revoked {token_type_hint} with Bearer auth")
    except Exception as e:
        logger.warning(f"Failed to revoke token: {e}")
        raise


async def revoke_server_tokens(
    server_name: str,
    server_config: Dict[str, Any],
    preserve_step_up_state: bool = False,
) -> None:
    """
    Revokes tokens on the OAuth server if revocation endpoint is available.
    Per RFC 7009, revoke refresh token first, then access token.
    """
    storage = _get_secure_storage()
    existing_data = storage.read()
    if not existing_data or not existing_data.get("mcp_oauth"):
        return
    
    server_key = get_server_key(server_name, server_config)
    token_data = existing_data.get("mcp_oauth", {}).get(server_key, {})
    
    # Attempt server-side revocation if there are tokens
    if token_data.get("access_token") or token_data.get("refresh_token"):
        try:
            # Get the auth server URL from discovery state or config
            as_url = (token_data.get("discovery_state", {}).get("authorization_server_url") 
                     or server_config.get("url", ""))
            
            metadata = await fetch_auth_server_metadata(
                server_name,
                as_url,
                server_config.get("oauth", {}).get("auth_server_metadata_url"),
            )
            
            if not metadata:
                logger.debug(f"No OAuth metadata found for {server_name}")
            else:
                revocation_endpoint = metadata.get("revocation_endpoint")
                if not revocation_endpoint:
                    logger.debug("Server does not support token revocation")
                else:
                    # Determine auth method
                    auth_methods = (metadata.get("revocation_endpoint_auth_methods_supported") 
                                   or metadata.get("token_endpoint_auth_methods_supported", []))
                    auth_method = "client_secret_post"
                    if auth_methods and "client_secret_basic" in auth_methods:
                        auth_method = "client_secret_basic"
                    
                    # Revoke refresh token first
                    if token_data.get("refresh_token"):
                        try:
                            await revoke_token(
                                server_name=server_name,
                                endpoint=revocation_endpoint,
                                token=token_data["refresh_token"],
                                token_type_hint="refresh_token",
                                client_id=token_data.get("client_id"),
                                client_secret=token_data.get("client_secret"),
                                access_token=token_data.get("access_token"),
                                auth_method=auth_method,
                            )
                        except Exception as e:
                            logger.debug(f"Failed to revoke refresh token: {e}")
                    
                    # Then revoke access token
                    if token_data.get("access_token"):
                        try:
                            await revoke_token(
                                server_name=server_name,
                                endpoint=revocation_endpoint,
                                token=token_data["access_token"],
                                token_type_hint="access_token",
                                client_id=token_data.get("client_id"),
                                client_secret=token_data.get("client_secret"),
                                access_token=token_data.get("access_token"),
                                auth_method=auth_method,
                            )
                        except Exception as e:
                            logger.debug(f"Failed to revoke access token: {e}")
        except Exception as e:
            logger.debug(f"Failed to revoke tokens: {e}")
    
    # Always clear local tokens
    clear_server_tokens_from_local_storage(server_name, server_config)
    
    # Preserve step-up state if requested
    if preserve_step_up_state and (token_data.get("step_up_scope") or token_data.get("discovery_state")):
        fresh_data = storage.read() or {}
        updated_entry = {
            "server_name": server_name,
            "server_url": server_config.get("url"),
            "access_token": fresh_data.get("mcp_oauth", {}).get(server_key, {}).get("access_token", ""),
            "expires_at": fresh_data.get("mcp_oauth", {}).get(server_key, {}).get("expires_at", 0),
        }
        if token_data.get("step_up_scope"):
            updated_entry["step_up_scope"] = token_data["step_up_scope"]
        if token_data.get("discovery_state"):
            updated_entry["discovery_state"] = {
                "authorization_server_url": token_data["discovery_state"].get("authorization_server_url"),
                "resource_metadata_url": token_data["discovery_state"].get("resource_metadata_url"),
            }
        
        fresh_data["mcp_oauth"] = fresh_data.get("mcp_oauth", {})
        fresh_data["mcp_oauth"][server_key] = updated_entry
        storage.update(fresh_data)
        logger.debug("Preserved step-up auth state across revocation")


def wrap_fetch_with_step_up_detection(
    base_fetch: Callable,
    provider: "MCPAuthProvider",
) -> Callable:
    """
    Wraps fetch to detect 403 insufficient_scope responses and mark step-up
    pending on the provider BEFORE the SDK's 403 handler calls auth().
    """
    async def wrapped_fetch(url: str, init: Optional[Dict[str, Any]] = None) -> Any:
        response = await base_fetch(url, init)
        if response.status == 403:
            www_auth = response.headers.get("WWW-Authenticate", "")
            if "insufficient_scope" in www_auth:
                match = www_auth.match(r'scope=(?:"([^"]+)"|([^\s,]+))')
                scope = None
                if match:
                    scope = match.group(1) or match.group(2)
                if scope:
                    provider.mark_step_up_pending(scope)
        return response
    
    return wrapped_fetch


# ============================================================================
# XAA (Cross-App Access) Authentication
# ============================================================================

XAA_FAILURE_STAGES = [
    "idp_login",
    "discovery",
    "token_exchange",
    "jwt_bearer",
]


async def perform_mcp_xaa_auth(
    server_name: str,
    server_config: Dict[str, Any],
    on_authorization_url: Callable[[str], None],
    abort_signal: Optional[Any] = None,
    skip_browser_open: bool = False,
) -> None:
    """
    XAA (Cross-App Access) auth implementation.
    
    One IdP browser login is reused across all XAA-configured MCP servers:
    1. Acquire an id_token from the IdP (cached; if missing/expired, runs OIDC flow)
    2. Run the RFC 8693 + RFC 7523 exchange (no browser)
    3. Save tokens to the same keychain slot as normal OAuth
    """
    if not server_config.get("oauth", {}).get("xaa"):
        raise ValueError("XAA: oauth.xaa must be set")
    
    # Get IdP config from settings (placeholder - would come from xaaIdp settings)
    idp_settings = _get_xaa_idp_settings()
    if not idp_settings:
        raise Error(
            "XAA: no IdP connection configured. Run 'claude mcp xaa setup --issuer <url> --client-id <id> --client-secret' to configure."
        )
    
    client_id = server_config.get("oauth", {}).get("client_id")
    if not client_id:
        raise Error(f"XAA: server '{server_name}' needs an AS client_id. Re-add with --client-id.")
    
    client_config = _get_mcp_client_config(server_name, server_config)
    client_secret = client_config.get("client_secret") if client_config else None
    if not client_secret:
        raise Error(f"XAA: AS client secret not found for '{server_name}'. Re-add with --client-secret.")
    
    logger.debug(f"{server_name}: XAA: starting cross-app access flow")
    
    # Get IdP client secret from separate storage
    idp_client_secret = _get_idp_client_secret(idp_settings.get("issuer", ""))
    
    _failure_stage = "idp_login"
    
    # Step 1: Acquire id_token from IdP
    try:
        id_token = await _acquire_idp_id_token(
            idp_issuer=idp_settings["issuer"],
            idp_client_id=idp_settings["client_id"],
            idp_client_secret=idp_client_secret,
            callback_port=idp_settings.get("callback_port"),
            on_authorization_url=on_authorization_url,
            skip_browser_open=skip_browser_open,
            abort_signal=abort_signal,
        )
    except Exception:
        if abort_signal and getattr(abort_signal, "aborted", False):
            raise AuthenticationCancelledError()
        raise
    
    # Step 2: Discover IdP token endpoint
    _failure_stage = "discovery"
    oidc = await _discover_oidc(idp_settings["issuer"])
    
    # Step 3: Run the RFC 8693 + RFC 7523 exchange
    _failure_stage = "token_exchange"
    try:
        tokens = await _perform_cross_app_access(
            server_url=server_config["url"],
            client_id=client_id,
            client_secret=client_secret,
            idp_client_id=idp_settings["client_id"],
            idp_client_secret=idp_client_secret,
            idp_id_token=id_token,
            idp_token_endpoint=oidc["token_endpoint"],
            server_name=server_name,
            abort_signal=abort_signal,
        )
    except Exception as e:
        if abort_signal and getattr(abort_signal, "aborted", False):
            raise AuthenticationCancelledError()
        
        error_msg = str(e)
        if "PRM discovery failed" in error_msg or "AS metadata discovery failed" in error_msg:
            _failure_stage = "discovery"
        elif "jwt-bearer" in error_msg:
            _failure_stage = "jwt_bearer"
        raise
    
    # Step 4: Save tokens
    storage = _get_secure_storage()
    existing_data = storage.read() or {}
    server_key = get_server_key(server_name, server_config)
    prev = existing_data.get("mcp_oauth", {}).get(server_key, {})
    
    storage.update({
        **existing_data,
        "mcp_oauth": {
            **existing_data.get("mcp_oauth", {}),
            server_key: {
                **prev,
                "server_name": server_name,
                "server_url": server_config["url"],
                "access_token": tokens.get("access_token", ""),
                "refresh_token": tokens.get("refresh_token") or prev.get("refresh_token"),
                "expires_at": int(time.time() * 1000) + (tokens.get("expires_in", 3600) * 1000),
                "scope": tokens.get("scope"),
                "client_id": client_id,
                "client_secret": client_secret,
                "discovery_state": {
                    "authorization_server_url": tokens.get("authorization_server_url", ""),
                },
            },
        },
    })
    
    logger.debug(f"{server_name}: XAA: tokens saved")


# ============================================================================
# Client Configuration Management
# ============================================================================

def save_mcp_client_secret(
    server_name: str,
    server_config: Dict[str, Any],
    client_secret: str,
) -> None:
    """Save OAuth client secret for a server."""
    storage = _get_secure_storage()
    existing_data = storage.read() or {}
    server_key = get_server_key(server_name, server_config)
    
    storage.update({
        **existing_data,
        "mcp_oauth_client_config": {
            **existing_data.get("mcp_oauth_client_config", {}),
            server_key: {"client_secret": client_secret},
        },
    })


def clear_mcp_client_config(
    server_name: str,
    server_config: Dict[str, Any],
) -> None:
    """Clear stored client configuration for a server."""
    storage = _get_secure_storage()
    existing_data = storage.read()
    if not existing_data or not existing_data.get("mcp_oauth_client_config"):
        return
    
    server_key = get_server_key(server_name, server_config)
    if server_key in existing_data.get("mcp_oauth_client_config", {}):
        del existing_data["mcp_oauth_client_config"][server_key]
        storage.update(existing_data)


def _get_mcp_client_config(
    server_name: str,
    server_config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Get stored client configuration for a server."""
    storage = _get_secure_storage()
    data = storage.read()
    if not data:
        return None
    
    server_key = get_server_key(server_name, server_config)
    return data.get("mcp_oauth_client_config", {}).get(server_key)


# ============================================================================
# XAA IdP Integration Helpers
# ============================================================================

def _get_xaa_idp_settings() -> Optional[Dict[str, Any]]:
    """Get XAA IdP settings from environment/config."""
    # In a full implementation, this would read from settings or environment
    issuer = os.environ.get("MCP_XAA_ISSUER")
    client_id = os.environ.get("MCP_XAA_CLIENT_ID")
    client_secret = os.environ.get("MCP_XAA_CLIENT_SECRET")
    callback_port = os.environ.get("MCP_XAA_CALLBACK_PORT")
    
    if not issuer or not client_id:
        return None
    
    return {
        "issuer": issuer,
        "client_id": client_id,
        "client_secret": client_secret,
        "callback_port": int(callback_port) if callback_port else None,
    }


def _get_idp_client_secret(issuer: str) -> Optional[str]:
    """Get IdP client secret from secure storage."""
    # In a full implementation, this would use keychain
    return os.environ.get(f"MCP_XAA_IDP_SECRET_{hashlib.sha256(issuer.encode()).hexdigest()[:16].upper()}")


async def _acquire_idp_id_token(
    idp_issuer: str,
    idp_client_id: str,
    idp_client_secret: Optional[str],
    callback_port: Optional[int],
    on_authorization_url: Callable[[str], None],
    skip_browser_open: bool,
    abort_signal: Optional[Any],
) -> str:
    """
    Acquire id_token from the IdP via OIDC authorization code flow.
    Uses cached token if available and not expired.
    """
    cached_token = _get_cached_idp_id_token(idp_issuer)
    if cached_token:
        return cached_token
    
    # Would implement full OIDC flow here with browser pop
    # For now, raise an error indicating interactive auth is needed
    raise Error(f"XAA: id_token not cached for {idp_issuer}. Interactive login required.")


def _get_cached_idp_id_token(issuer: str) -> Optional[str]:
    """Get cached IdP id_token from storage."""
    storage = _get_secure_storage()
    data = storage.read()
    if not data:
        return None
    
    idp_tokens = data.get("mcp_xaa_idp_tokens", {})
    entry = idp_tokens.get(issuer, {})
    
    expires_at = entry.get("expires_at", 0)
    if expires_at > 0 and int(time.time() * 1000) >= expires_at:
        return None
    
    return entry.get("id_token")


def _clear_idp_id_token(issuer: str) -> None:
    """Clear cached IdP id_token."""
    storage = _get_secure_storage()
    existing_data = storage.read() or {}
    
    idp_tokens = existing_data.get("mcp_xaa_idp_tokens", {})
    if issuer in idp_tokens:
        del idp_tokens[issuer]
        existing_data["mcp_xaa_idp_tokens"] = idp_tokens
        storage.update(existing_data)


async def _discover_oidc(issuer: str) -> Dict[str, Any]:
    """
    Discover OIDC endpoints from the IdP.
    Implements OIDC Discovery (RFC 8414).
    """
    import aiohttp
    
    well_known_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(well_known_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.ok:
                    return await response.json()
    except Exception as e:
        logger.debug(f"OIDC discovery failed for {issuer}: {e}")
    
    # Fallback: construct from issuer
    return {
        "token_endpoint": f"{issuer.rstrip('/')}/oauth/token",
        "authorization_endpoint": f"{issuer.rstrip('/')}/oauth/authorize",
    }


async def _perform_cross_app_access(
    server_url: str,
    client_id: str,
    client_secret: str,
    idp_client_id: str,
    idp_client_secret: Optional[str],
    idp_id_token: str,
    idp_token_endpoint: str,
    server_name: str,
    abort_signal: Optional[Any],
) -> Dict[str, Any]:
    """
    Perform RFC 8693 token exchange (Cross-App Access).
    Exchanges IdP id_token for AS access token.
    """
    logger.debug(f"Performing cross-app access for {server_name}")
    
    # In full implementation:
    # 1. Discover AS endpoints from server_url
    # 2. Exchange id_token using RFC 8693 jwt-bearer grant type
    # 3. Return the access_token
    
    raise Error("XAA token exchange not fully implemented")


# ============================================================================
# Scope Helper Functions
# ============================================================================

def get_scope_from_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Safely extracts scope information from AuthorizationServerMetadata.
    Different providers use different fields for scope information.
    """
    if not metadata:
        return None
    
    if "scope" in metadata and isinstance(metadata["scope"], str):
        return metadata["scope"]
    
    if "default_scope" in metadata and isinstance(metadata["default_scope"], str):
        return metadata["default_scope"]
    
    if "scopes_supported" in metadata and isinstance(metadata["scopes_supported"], list):
        return " ".join(metadata["scopes_supported"])
    
    return None


def parse_www_authenticate_header(header: str) -> Dict[str, Any]:
    """
    Parse WWW-Authenticate header per RFC 6750.
    Extracts challenge parameters for Bearer token errors.
    """
    result = {}
    parts = header.split()
    
    if not parts:
        return result
    
    result["scheme"] = parts[0].lower()
    
    param_string = " ".join(parts[1:]) if len(parts) > 1 else ""
    
    import re
    for match in re.finditer(r'(\w+)(?:="([^"]*)"|=([^\s,]+))', param_string):
        key = match.group(1)
        value = match.group(2) or match.group(3)
        result[key] = value
    
    return result


def is_token_expired(expires_at: int) -> bool:
    """Check if a token is expired based on expires_at timestamp (ms)."""
    if expires_at <= 0:
        return True
    return int(time.time() * 1000) >= expires_at


def is_token_expiring_soon(expires_at: int, threshold_seconds: int = 300) -> bool:
    """Check if token will expire within threshold."""
    if expires_at <= 0:
        return True
    remaining = (expires_at - int(time.time() * 1000)) / 1000
    return remaining <= threshold_seconds


async def read_client_secret() -> str:
    """Read OAuth client secret from environment or stdin."""
    env_secret = os.environ.get("MCP_CLIENT_SECRET")
    if env_secret:
        return env_secret
    
    if not sys.stdin.isatty():
        raise Error(
            "No TTY available to prompt for client secret. Set MCP_CLIENT_SECRET env var instead."
        )
    
    import termios
    import tty
    
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        tty.setraw(fd)
        sys.stderr.write("Enter OAuth client secret: ")
        sys.stderr.flush()
        secret = ""
        while True:
            ch = sys.stdin.read(1)
            if ch == "\n" or ch == "\r":
                sys.stderr.write("\n")
                break
            elif ch == "\x03":  # Ctrl-C
                raise Error("Cancelled")
            elif ch == "\x7f" or ch == "\b":  # Backspace
                if secret:
                    secret = secret[:-1]
                    sys.stderr.write("\b \b")
                    sys.stderr.flush()
            else:
                secret += ch
                sys.stderr.write("*")
                sys.stderr.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    return secret


# ============================================================================
# Error Classes
# ============================================================================

class Error(Exception):
    """Base error class for MCP auth."""
    pass


class XaaTokenExchangeError(Error):
    """Error during XAA token exchange."""
    def __init__(self, message: str, should_clear_id_token: bool = False):
        super().__init__(message)
        self.should_clear_id_token = should_clear_id_token
