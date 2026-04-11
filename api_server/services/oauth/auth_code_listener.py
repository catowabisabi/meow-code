"""AuthCodeListener - HTTP server for capturing OAuth authorization code redirects."""

import asyncio
from typing import Callable, Optional

from .config import get_oauth_config
from .client import should_use_claude_ai_auth


class AuthCodeListener:
    """
    Temporary localhost HTTP server that listens for OAuth authorization code redirects.
    
    When the user authorizes in their browser, the OAuth provider redirects to:
    http://localhost:[port]/callback?code=AUTH_CODE&state=STATE
    
    This server captures that redirect and extracts the auth code.
    Note: This is NOT an OAuth server - it's just a redirect capture mechanism.
    """

    def __init__(self, callback_path: str = "/callback"):
        self._server: Optional[asyncio.Server] = None
        self.port: int = 0
        self.promise_resolver: Optional[Callable[[str], None]] = None
        self.promise_rejecter: Optional[Callable[[Exception], None]] = None
        self.expected_state: Optional[str] = None
        self.pending_response: Optional["_PendingResponse"] = None
        self.callback_path = callback_path
        self._ready_callback: Optional[Callable[[], None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self, port: Optional[int] = None) -> int:
        """
        Start listening on an OS-assigned port and return the port number.
        This avoids race conditions by keeping the server open until it's used.
        """
        self._loop = asyncio.get_event_loop()
        
        async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await _handle_request(reader, writer, self)
        
        try:
            if port:
                self._server = await self._loop.create_server(
                    lambda: _OAuthRequestHandler(self),
                    host="localhost",
                    port=port,
                )
                self.port = port
            else:
                self._server = await self._loop.create_server(
                    lambda: _OAuthRequestHandler(self),
                    host="localhost",
                    port=0,
                )
                sockets = self._server.sockets
                if sockets:
                    self.port = sockets[0].getsockname()[1]
                else:
                    self.port = 0
            return self.port
        except Exception as e:
            raise Exception(f"Failed to start OAuth callback server: {e}")

    def get_port(self) -> int:
        """Get the port the server is listening on."""
        return self.port

    def has_pending_response(self) -> bool:
        """Check if there's a pending response waiting."""
        return self.pending_response is not None

    async def wait_for_authorization(
        self,
        state: str,
        on_ready: Callable[[], None],
    ) -> str:
        """
        Wait for authorization code with state validation.
        """
        self.expected_state = state
        self._ready_callback = on_ready
        
        if self._ready_callback:
            self._ready_callback()
        
        future = asyncio.Future()
        self.promise_resolver = lambda code: future.set_result(code)
        self.promise_rejecter = lambda err: future.set_exception(err)
        
        return await future

    def handle_success_redirect(self, scopes: list[str]) -> None:
        """
        Complete the OAuth flow by redirecting the user's browser to a success page.
        Different success pages are shown based on the granted scopes.
        """
        if not self.pending_response:
            return
        
        config = get_oauth_config()
        success_url = (
            config.claudenai_success_url
            if should_use_claude_ai_auth(scopes)
            else config.console_success_url
        )
        
        self.pending_response.write_redirect(302, success_url)
        self.pending_response = None

    def handle_error_redirect(self) -> None:
        """
        Handle error case by sending a redirect to the appropriate success page with an error indicator.
        """
        if not self.pending_response:
            return
        
        config = get_oauth_config()
        error_url = config.claudenai_success_url
        
        self.pending_response.write_redirect(302, error_url)
        self.pending_response = None

    def validate_and_respond(
        self,
        auth_code: Optional[str],
        state: Optional[str],
    ) -> bool:
        """
        Validate the authorization code and state.
        
        Returns:
            True if valid, False otherwise
        """
        if not auth_code:
            self.reject(Exception("No authorization code received"))
            return False
        
        if state != self.expected_state:
            self.reject(Exception("Invalid state parameter"))
            return False
        
        self.pending_response = _PendingResponse()
        self.resolve(auth_code)
        return True

    def resolve(self, authorization_code: str) -> None:
        """Resolve the promise with the authorization code."""
        if self.promise_resolver:
            self.promise_resolver(authorization_code)
            self.promise_resolver = None
            self.promise_rejecter = None

    def reject(self, error: Exception) -> None:
        """Reject the promise with an error."""
        if self.promise_rejecter:
            self.promise_rejecter(error)
            self.promise_resolver = None
            self.promise_rejecter = None

    def close(self) -> None:
        """Close the server and cleanup resources."""
        if self.pending_response:
            self.handle_error_redirect()
        
        if self._server:
            self._server.close()
            self._server = None
        
        self.promise_resolver = None
        self.promise_rejecter = None
        self._ready_callback = None


class _PendingResponse:
    """Holds pending response information for deferred redirect."""
    
    def __init__(self):
        self.status_code: int = 0
        self.headers: dict = {}
        self.body: bytes = b""
        self._should_redirect: bool = False
        self._redirect_location: Optional[str] = None
    
    def write_redirect(self, status_code: int, location: str) -> None:
        """Prepare a redirect response."""
        self.status_code = status_code
        self._should_redirect = True
        self._redirect_location = location
    
    def write_head(self, status_code: int, headers: dict) -> None:
        """Set status and headers for response."""
        self.status_code = status_code
        self.headers = headers


class _OAuthRequestHandler(asyncio.Protocol):
    """Async request handler for OAuth callback."""
    
    def __init__(self, listener: AuthCodeListener):
        self.listener = listener
        self._transport: asyncio.Transport = None
    
    def connection_made(self, transport: asyncio.Transport) -> None:
        self._transport = transport
    
    def data_received(self, data: bytes) -> None:
        """Handle incoming data."""
        asyncio.ensure_future(self._process_data(data))
    
    async def _process_data(self, data: bytes) -> None:
        """Process the HTTP request data."""
        try:
            from urllib.parse import parse_qs, urlparse
            
            text = data.decode("utf-8", errors="ignore")
            lines = text.split("\r\n")
            
            if not lines:
                return
            
            request_line = lines[0]
            if not request_line.startswith("GET "):
                return
            
            parts = request_line.split(" ")
            if len(parts) < 2:
                return
            
            path_with_query = parts[1]
            parsed = urlparse(path_with_query)
            query_params = parse_qs(parsed.query)
            
            if parsed.path != self.listener.callback_path:
                response = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
                self._transport.write(response)
                self._transport.close()
                return
            
            auth_code = query_params.get("code", [None])[0]
            state = query_params.get("state", [None])[0]
            
            is_valid = self.listener.validate_and_respond(auth_code, state)
            
            if not is_valid:
                response = b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n"
                self._transport.write(response)
                self._transport.close()
                return
            
            response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
            self._transport.write(response)
            self._transport.close()
            
        except Exception as e:
            self.listener.reject(e)
            self._transport.close()


async def _handle_request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    listener: AuthCodeListener,
) -> None:
    """Handle incoming OAuth callback request."""
    from urllib.parse import parse_qs, urlparse
    
    try:
        data = await reader.read(4096)
        if not data:
            return
        
        text = data.decode("utf-8", errors="ignore")
        lines = text.split("\r\n")
        
        if not lines:
            return
        
        request_line = lines[0]
        if not request_line.startswith("GET "):
            return
        
        parts = request_line.split(" ")
        if len(parts) < 2:
            return
        
        path_with_query = parts[1]
        parsed = urlparse(path_with_query)
        query_params = parse_qs(parsed.query)
        
        if parsed.path != listener.callback_path:
            response = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
            writer.write(response.encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return
        
        auth_code = query_params.get("code", [None])[0]
        state = query_params.get("state", [None])[0]
        
        is_valid = listener.validate_and_respond(auth_code, state)
        
        if not is_valid:
            response = "HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n"
            writer.write(response.encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return
        
        response = "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
        writer.write(response.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        
    except Exception as e:
        listener.reject(e)
        writer.close()
        await writer.wait_closed()
