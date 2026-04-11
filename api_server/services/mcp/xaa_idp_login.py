"""
XAA IdP Login — acquires an OIDC id_token from an enterprise IdP via the
standard authorization_code + PKCE flow, then caches it by IdP issuer.
"""

import asyncio
import base64
import json
import os
import random
import socket
import time
import urllib.parse
from typing import Any, Callable, Dict, Optional

import httpx

IDP_LOGIN_TIMEOUT_MS = 5 * 60 * 1000
IDP_REQUEST_TIMEOUT_MS = 30000
ID_TOKEN_EXPIRY_BUFFER_S = 60


def is_xaa_enabled() -> bool:
    """Check if XAA is enabled via environment."""
    return os.environ.get("CLAUDE_CODE_ENABLE_XAA", "").lower() not in ("false", "0", "no", "")


class XaaIdpSettings:
    """XAA IdP settings from configuration."""
    def __init__(self, issuer: str, client_id: str, callback_port: Optional[int] = None):
        self.issuer = issuer
        self.client_id = client_id
        self.callback_port = callback_port


def get_xaa_idp_settings() -> Optional[XaaIdpSettings]:
    """Get XAA IdP settings from initial settings."""
    return None


def issuer_key(issuer: str) -> str:
    """
    Normalize IdP issuer URL for use as cache key.

    Args:
        issuer: Issuer URL

    Returns:
        Normalized cache key
    """
    try:
        parsed = urllib.parse.urlparse(issuer)
        normalized = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            "",
            "",
        ))
        return normalized
    except Exception:
        return issuer.rstrip("/")


def _get_secure_storage() -> Dict[str, Any]:
    """Get secure storage data."""
    return {}


def _save_secure_storage(data: Dict[str, Any]) -> None:
    """Save secure storage data."""
    pass


def get_cached_idp_id_token(idp_issuer: str) -> Optional[str]:
    """
    Read cached id_token for the given IdP issuer.

    Returns None if missing or within buffer of expiring.
    """
    data = _get_secure_storage()
    entry = data.get("mcpXaaIdp", {}).get(issuer_key(idp_issuer))
    if not entry:
        return None

    remaining_ms = entry.get("expiresAt", 0) - time.time() * 1000
    if remaining_ms <= ID_TOKEN_EXPIRY_BUFFER_S * 1000:
        return None

    return entry.get("idToken")


def save_idp_id_token(idp_issuer: str, id_token: str, expires_at: int) -> None:
    """Save id_token to secure storage cache."""
    data = _get_secure_storage()
    mcp_xaa_idp = data.get("mcpXaaIdp", {})
    mcp_xaa_idp[issuer_key(idp_issuer)] = {"idToken": id_token, "expiresAt": expires_at}
    data["mcpXaaIdp"] = mcp_xaa_idp
    _save_secure_storage(data)


def save_idp_id_token_from_jwt(idp_issuer: str, id_token: str) -> int:
    """
    Save externally-obtained id_token into XAA cache.

    Returns expiresAt computed from JWT exp claim.
    """
    exp = _jwt_exp(id_token)
    expires_at = exp * 1000 if exp else time.time() * 1000 + 3600 * 1000
    save_idp_id_token(idp_issuer, id_token, expires_at)
    return expires_at


def clear_idp_id_token(idp_issuer: str) -> None:
    """Remove cached id_token for the given issuer."""
    data = _get_secure_storage()
    key = issuer_key(idp_issuer)
    if data.get("mcpXaaIdp", {}).get(key):
        del data["mcpXaaIdp"][key]
        _save_secure_storage(data)


def save_idp_client_secret(idp_issuer: str, client_secret: str) -> Dict[str, Any]:
    """Save IdP client secret to secure storage."""
    data = _get_secure_storage()
    mcp_xaa_idp_config = data.get("mcpXaaIdpConfig", {})
    mcp_xaa_idp_config[issuer_key(idp_issuer)] = {"clientSecret": client_secret}
    data["mcpXaaIdpConfig"] = mcp_xaa_idp_config
    _save_secure_storage(data)
    return {"success": True}


def get_idp_client_secret(idp_issuer: str) -> Optional[str]:
    """Read IdP client secret from secure storage."""
    data = _get_secure_storage()
    return data.get("mcpXaaIdpConfig", {}).get(issuer_key(idp_issuer), {}).get("clientSecret")


def clear_idp_client_secret(idp_issuer: str) -> None:
    """Remove IdP client secret for the given issuer."""
    data = _get_secure_storage()
    key = issuer_key(idp_issuer)
    if data.get("mcpXaaIdpConfig", {}).get(key):
        del data["mcpXaaIdpConfig"][key]
        _save_secure_storage(data)


def _jwt_exp(jwt: str) -> Optional[int]:
    """
    Decode exp claim from JWT without verification.

    Used only to derive cache TTL.
    """
    parts = jwt.split(".")
    if len(parts) != 3:
        return None

    try:
        payload_str = base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8")
        payload = json.loads(payload_str)
        return payload.get("exp") if isinstance(payload, dict) else None
    except Exception:
        return None


async def discover_oidc(idp_issuer: str) -> Dict[str, Any]:
    """
    OIDC Discovery per RFC 4.1.

    Args:
        idp_issuer: IdP issuer URL

    Returns:
        OpenID provider discovery metadata
    """
    base = idp_issuer if idp_issuer.endswith("/") else f"{idp_issuer}/"
    url = f"{base}.well-known/openid-configuration"

    async with httpx.AsyncClient(timeout=IDP_REQUEST_TIMEOUT_MS / 1000) as client:
        response = await client.get(url, headers={"Accept": "application/json"})
        if not response.is_success:
            raise Exception(f"OIDC discovery failed: HTTP {response.status_code} at {url}")

        try:
            return response.json()
        except Exception:
            raise Exception(f"OIDC discovery returned non-JSON at {url}")


async def _wait_for_callback(
    port: int,
    expected_state: str,
    abort_signal: Optional[Any] = None,
    on_listening: Optional[Callable[[], None]] = None,
) -> str:
    """
    Wait for OAuth authorization code on local callback server.

    Args:
        port: Callback port
        expected_state: Expected state parameter
        abort_signal: Optional abort signal
        on_listening: Callback when server is listening

    Returns:
        Authorization code
    """
    callback_received = asyncio.Event()

    async def handle_callback(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        nonlocal callback_received
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                return

            decoded = request_line.decode("utf-8", errors="replace")
            path = decoded.split(" ")[1] if " " in decoded else "/"

            parsed = urllib.parse.urlparse(path)
            query = urllib.parse.parse_qs(parsed.query)

            code = query.get("code", [None])[0]
            state = query.get("state", [None])[0]
            error = query.get("error", [None])[0]

            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body><h3>IdP login complete</h3></body></html>"

            if error:
                response = "HTTP/1.1 400 Bad Request\r\nContent-Type: text/html\r\n\r\n<html><body><h3>IdP login failed</h3></body></html>"
                writer.write(response.encode())
                writer.close()
                callback_received.set()
                return

            if state != expected_state:
                response = "HTTP/1.1 400 Bad Request\r\nContent-Type: text/html\r\n\r\n<html><body><h3>State mismatch</h3></body></html>"
                writer.write(response.encode())
                writer.close()
                callback_received.set()
                return

            if not code:
                response = "HTTP/1.1 400 Bad Request\r\nContent-Type: text/html\r\n\r\n<html><body><h3>Missing code</h3></body></html>"
                writer.write(response.encode())
                writer.close()
                callback_received.set()
                return

            writer.write(response.encode())
            writer.close()

            if callback_received.is_set():
                return
            callback_received.set()
            return code

        except Exception:
            writer.close()
            callback_received.set()

    server = await asyncio.start_server(handle_callback, "127.0.0.1", port)

    if on_listening:
        on_listening()

    try:
        async with asyncio.timeout(IDP_LOGIN_TIMEOUT_MS / 1000):
            await callback_received.wait()
    except asyncio.TimeoutError:
        server.close()
        raise Exception("XAA IdP: login timed out")

    server.close()
    await server.wait_closed()

    return ""


class IdpLoginOptions:
    """Options for IdP login."""
    def __init__(
        self,
        idp_issuer: str,
        idp_client_id: str,
        idp_client_secret: Optional[str] = None,
        callback_port: Optional[int] = None,
        on_authorization_url: Optional[Callable[[str], None]] = None,
        skip_browser_open: bool = False,
        abort_signal: Optional[Any] = None,
    ):
        self.idp_issuer = idp_issuer
        self.idp_client_id = idp_client_id
        self.idp_client_secret = idp_client_secret
        self.callback_port = callback_port
        self.on_authorization_url = on_authorization_url
        self.skip_browser_open = skip_browser_open
        self.abort_signal = abort_signal


async def acquire_idp_id_token(opts: IdpLoginOptions) -> str:
    """
    Acquire id_token from IdP: return cached if valid, otherwise run OIDC flow.

    Args:
        opts: Login options

    Returns:
        id_token string
    """
    cached = get_cached_idp_id_token(opts.idp_issuer)
    if cached:
        return cached

    metadata = await discover_oidc(opts.idp_issuer)

    if opts.callback_port:
        port = opts.callback_port
    else:
        port = await _find_available_port()

    redirect_uri = f"http://localhost:{port}/callback"
    state = _random_base64url(32)
    code_verifier = _random_base64url(32)

    auth_url = _build_authorization_url(
        metadata.get("authorization_endpoint", ""),
        opts.idp_client_id,
        redirect_uri,
        state,
        code_verifier,
    )

    if opts.on_authorization_url:
        opts.on_authorization_url(auth_url)

    code = await _wait_for_callback(port, state, opts.abort_signal)

    tokens = await _exchange_authorization_code(
        metadata.get("token_endpoint", ""),
        opts.idp_client_id,
        opts.idp_client_secret,
        code,
        code_verifier,
        redirect_uri,
    )

    if not tokens.get("id_token"):
        raise Exception("Token response missing id_token (check scope=openid)")

    exp = _jwt_exp(tokens["id_token"])
    expires_at = exp * 1000 if exp else time.time() * 1000 + (tokens.get("expires_in", 3600) * 1000)

    save_idp_id_token(opts.idp_issuer, tokens["id_token"], expires_at)

    return tokens["id_token"]


def _random_base64url(length: int) -> str:
    """Generate random base64url string."""
    bytes_data = bytes(random.getrandbits(8) for _ in range(length))
    return base64.urlsafe_b64encode(bytes_data).rstrip(b"=").decode("utf-8")


def _build_authorization_url(
    authorization_endpoint: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_verifier: str,
) -> str:
    """Build OAuth authorization URL."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": _pkce_challenge(code_verifier),
        "code_challenge_method": "S256",
        "scope": "openid",
    }
    return f"{authorization_endpoint}?{urllib.parse.urlencode(params)}"


def _pkce_challenge(code_verifier: str) -> str:
    """Generate PKCE code challenge from verifier."""
    import hashlib
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")


async def _exchange_authorization_code(
    token_endpoint: str,
    client_id: str,
    client_secret: Optional[str],
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> Dict[str, Any]:
    """Exchange authorization code for tokens."""
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
        "client_id": client_id,
    }
    if client_secret:
        params["client_secret"] = client_secret

    async with httpx.AsyncClient(timeout=IDP_REQUEST_TIMEOUT_MS / 1000) as client:
        response = await client.post(
            token_endpoint,
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if not response.is_success:
            raise Exception(f"Token exchange failed: HTTP {response.status_code}")
        return response.json()


async def _find_available_port() -> int:
    """Find an available port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
