"""
Cross-App Access (XAA) / Enterprise Managed Authorization.

Obtains an MCP access token WITHOUT a browser consent screen by chaining:
  1. RFC 8693 Token Exchange at the IdP: id_token → ID-JAG
  2. RFC 7523 JWT Bearer Grant at the AS: ID-JAG → access_token
"""

import base64
import json
import os
import time
import urllib.parse
from typing import Any, Callable, Dict, Optional, Tuple

import httpx

XAA_REQUEST_TIMEOUT_MS = 30000

TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange"
JWT_BEARER_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"
ID_JAG_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:id-jag"
ID_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:id_token"

SENSITIVE_TOKEN_RE = '"(access_token|refresh_token|id_token|assertion|subject_token|client_secret)"\\s*:\\s*"[^"]*"'


def _redact_tokens(raw: Any) -> str:
    """Redact sensitive tokens from logs."""
    import re
    s = json.dumps(raw) if not isinstance(raw, str) else raw
    return re.sub(SENSITIVE_TOKEN_RE, '"\g<1>":"[REDACTED]"', s)


def _normalize_url(url: str) -> str:
    """Normalize URL for comparison (RFC 3986 §6.2.2)."""
    try:
        parsed = urllib.parse.urlparse(url)
        normalized = urllib.parse.urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.params,
            parsed.query,
            "",
        ))
        return normalized
    except Exception:
        return url.rstrip("/")


class XaaTokenExchangeError(Exception):
    """Error during XAA token exchange."""
    def __init__(self, message: str, should_clear_id_token: bool):
        super().__init__(message)
        self.should_clear_id_token = should_clear_id_token


class ProtectedResourceMetadata:
    """RFC 9728 PRM discovery result."""
    def __init__(self, resource: str, authorization_servers: list):
        self.resource = resource
        self.authorization_servers = authorization_servers


class AuthorizationServerMetadata:
    """RFC 8414 AS metadata."""
    def __init__(self, issuer: str, token_endpoint: str, grant_types_supported: Optional[list] = None, token_endpoint_auth_methods_supported: Optional[list] = None):
        self.issuer = issuer
        self.token_endpoint = token_endpoint
        self.grant_types_supported = grant_types_supported
        self.token_endpoint_auth_methods_supported = token_endpoint_auth_methods_supported


class JwtAuthGrantResult:
    """Result of RFC 8693 token exchange."""
    def __init__(self, jwt_auth_grant: str, expires_in: Optional[int] = None, scope: Optional[str] = None):
        self.jwt_auth_grant = jwt_auth_grant
        self.expires_in = expires_in
        self.scope = scope


class XaaTokenResult:
    """XAA token result."""
    def __init__(self, access_token: str, token_type: str, expires_in: Optional[int] = None, scope: Optional[str] = None, refresh_token: Optional[str] = None, authorization_server_url: Optional[str] = None):
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.scope = scope
        self.refresh_token = refresh_token
        self.authorization_server_url = authorization_server_url


async def discover_protected_resource(
    server_url: str,
    fetch_fn: Optional[Callable[..., Any]] = None,
) -> ProtectedResourceMetadata:
    """
    RFC 9728 PRM discovery via SDK.

    Args:
        server_url: The MCP server URL
        fetch_fn: Optional custom fetch function

    Returns:
        ProtectedResourceMetadata with resource and authorization_servers
    """
    async def do_fetch(url: str, **kwargs) -> httpx.Response:
        client = httpx.AsyncClient(timeout=XAA_REQUEST_TIMEOUT_MS / 1000)
        return await client.get(url, **kwargs)

    fetch = fetch_fn or do_fetch

    try:
        prm_url = f"{server_url.rstrip('/')}/.well-known/oauth-protected-resource"
        response = await fetch(prm_url)
        data = response.json()
        return ProtectedResourceMetadata(
            resource=data.get("resource", server_url),
            authorization_servers=data.get("authorization_servers", [server_url]),
        )
    except Exception as e:
        raise XaaTokenExchangeError(f"PRM discovery failed: {e}", False)


async def discover_authorization_server(
    as_url: str,
    fetch_fn: Optional[Callable[..., Any]] = None,
) -> AuthorizationServerMetadata:
    """
    RFC 8414 AS metadata discovery.

    Args:
        as_url: Authorization server URL
        fetch_fn: Optional custom fetch function

    Returns:
        AuthorizationServerMetadata
    """
    async def do_fetch(url: str, **kwargs) -> httpx.Response:
        client = httpx.AsyncClient(timeout=XAA_REQUEST_TIMEOUT_MS / 1000)
        return await client.get(url, **kwargs)

    fetch = fetch_fn or do_fetch

    try:
        response = await fetch(as_url)
        data = response.json()
        return AuthorizationServerMetadata(
            issuer=data.get("issuer", as_url),
            token_endpoint=data.get("token_endpoint", ""),
            grant_types_supported=data.get("grant_types_supported"),
            token_endpoint_auth_methods_supported=data.get("token_endpoint_auth_methods_supported"),
        )
    except Exception as e:
        raise XaaTokenExchangeError(f"AS metadata discovery failed: {e}", False)


async def request_jwt_authorization_grant(
    token_endpoint: str,
    audience: str,
    resource: str,
    id_token: str,
    client_id: str,
    client_secret: Optional[str] = None,
    scope: Optional[str] = None,
    fetch_fn: Optional[Callable[..., Any]] = None,
) -> JwtAuthGrantResult:
    """
    RFC 8693 Token Exchange at IdP: id_token → ID-JAG.

    Args:
        token_endpoint: IdP token endpoint
        audience: Audience for the token exchange
        resource: Resource identifier
        id_token: OIDC id_token from IdP
        client_id: Client ID at IdP
        client_secret: Optional client secret
        scope: Optional scope
        fetch_fn: Optional custom fetch function

    Returns:
        JwtAuthGrantResult with ID-JAG
    """
    async def do_fetch(url: str, **kwargs) -> httpx.Response:
        client = httpx.AsyncClient(timeout=XAA_REQUEST_TIMEOUT_MS / 1000)
        return await client.post(url, **kwargs)

    fetch = fetch_fn or do_fetch

    params = {
        "grant_type": TOKEN_EXCHANGE_GRANT,
        "requested_token_type": ID_JAG_TOKEN_TYPE,
        "audience": audience,
        "resource": resource,
        "subject_token": id_token,
        "subject_token_type": ID_TOKEN_TYPE,
        "client_id": client_id,
    }
    if client_secret:
        params["client_secret"] = client_secret
    if scope:
        params["scope"] = scope

    try:
        response = await fetch(
            token_endpoint,
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if not response.is_success:
            should_clear = response.status_code < 500
            raise XaaTokenExchangeError(
                f"Token exchange failed: HTTP {response.status_code}",
                should_clear,
            )

        data = response.json()
        if "access_token" not in data:
            raise XaaTokenExchangeError("Token exchange response missing access_token", True)
        if data.get("issued_token_type") != ID_JAG_TOKEN_TYPE:
            raise XaaTokenExchangeError(
                f"Unexpected issued_token_type: {data.get('issued_token_type')}",
                True,
            )

        return JwtAuthGrantResult(
            jwt_auth_grant=data["access_token"],
            expires_in=data.get("expires_in"),
            scope=data.get("scope"),
        )
    except httpx.HTTPError as e:
        raise XaaTokenExchangeError(f"Token exchange HTTP error: {e}", False)


async def exchange_jwt_auth_grant(
    token_endpoint: str,
    assertion: str,
    client_id: str,
    client_secret: str,
    auth_method: str = "client_secret_basic",
    scope: Optional[str] = None,
    fetch_fn: Optional[Callable[..., Any]] = None,
) -> XaaTokenResult:
    """
    RFC 7523 JWT Bearer Grant at AS: ID-JAG → access_token.

    Args:
        token_endpoint: AS token endpoint
        assertion: ID-JAG assertion
        client_id: Client ID at AS
        client_secret: Client secret at AS
        auth_method: Auth method (client_secret_basic or client_secret_post)
        scope: Optional scope
        fetch_fn: Optional custom fetch function

    Returns:
        XaaTokenResult with access_token
    """
    async def do_fetch(url: str, **kwargs) -> httpx.Response:
        client = httpx.AsyncClient(timeout=XAA_REQUEST_TIMEOUT_MS / 1000)
        return await client.post(url, **kwargs)

    fetch = fetch_fn or do_fetch

    params = {
        "grant_type": JWT_BEARER_GRANT,
        "assertion": assertion,
    }
    if scope:
        params["scope"] = scope

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if auth_method == "client_secret_basic":
        auth_string = f"{urllib.parse.quote(client_id)}:{urllib.parse.quote(client_secret)}"
        headers["Authorization"] = f"Basic {base64.b64encode(auth_string.encode()).decode()}"
    else:
        params["client_id"] = client_id
        params["client_secret"] = client_secret

    try:
        response = await fetch(
            token_endpoint,
            data=params,
            headers=headers,
        )

        if not response.is_success:
            raise Exception(f"JWT bearer grant failed: HTTP {response.status_code}")

        data = response.json()
        return XaaTokenResult(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in"),
            scope=data.get("scope"),
            refresh_token=data.get("refresh_token"),
        )
    except httpx.HTTPError as e:
        raise Exception(f"JWT bearer grant HTTP error: {e}")


class XaaConfig:
    """Configuration for XAA flow."""
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        idp_client_id: str,
        idp_client_secret: Optional[str] = None,
        idp_id_token: str = "",
        idp_token_endpoint: str = "",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.idp_client_id = idp_client_id
        self.idp_client_secret = idp_client_secret
        self.idp_id_token = idp_id_token
        self.idp_token_endpoint = idp_token_endpoint


async def perform_cross_app_access(
    server_url: str,
    config: XaaConfig,
    server_name: str = "xaa",
    abort_signal: Optional[Any] = None,
) -> XaaTokenResult:
    """
    Full XAA flow: PRM → AS metadata → token-exchange → jwt-bearer → access_token.

    Args:
        server_url: The MCP server URL
        config: XAA configuration with IdP + AS credentials
        server_name: Server name for logging
        abort_signal: Optional abort signal

    Returns:
        XaaTokenResult with access_token and authorizationServerUrl
    """
    prm = await discover_protected_resource(server_url)

    as_meta: Optional[AuthorizationServerMetadata] = None
    as_errors: list = []

    for as_url in prm.authorization_servers:
        try:
            candidate = await discover_authorization_server(as_url)
            if candidate.grant_types_supported and JWT_BEARER_GRANT not in candidate.grant_types_supported:
                as_errors.append(f"{as_url}: does not advertise jwt-bearer")
                continue
            as_meta = candidate
            break
        except Exception as e:
            as_errors.append(f"{as_url}: {e}")
            continue

    if not as_meta:
        raise Exception(f"No authorization server supports jwt-bearer. Tried: {'; '.join(as_errors)}")

    auth_method = "client_secret_basic"
    if as_meta.token_endpoint_auth_methods_supported:
        if "client_secret_basic" not in as_meta.token_endpoint_auth_methods_supported and "client_secret_post" in as_meta.token_endpoint_auth_methods_supported:
            auth_method = "client_secret_post"

    jag = await request_jwt_authorization_grant(
        token_endpoint=config.idp_token_endpoint,
        audience=as_meta.issuer,
        resource=prm.resource,
        id_token=config.idp_id_token,
        client_id=config.idp_client_id,
        client_secret=config.idp_client_secret,
    )

    tokens = await exchange_jwt_auth_grant(
        token_endpoint=as_meta.token_endpoint,
        assertion=jag.jwt_auth_grant,
        client_id=config.client_id,
        client_secret=config.client_secret,
        auth_method=auth_method,
    )

    tokens.authorization_server_url = as_meta.issuer
    return tokens
