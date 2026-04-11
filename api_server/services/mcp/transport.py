"""Transport implementations for MCP service."""

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TransportClosedError(Exception):
    """Raised when transport is closed."""
    pass


@dataclass
class JSONRPCMessage:
    """JSON-RPC message for MCP communication."""
    jsonrpc: str = "2.0"
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class Transport:
    """
    Base class for MCP transports.
    Handles sending and receiving JSON-RPC messages.
    """

    def __init__(self):
        self._closed = False
        self.onclose: Optional[Callable[[], None]] = None
        self.onerror: Optional[Callable[[Exception], None]] = None
        self.onmessage: Optional[Callable[[Dict[str, Any]], None]] = None

    async def start(self) -> None:
        """Start the transport."""
        raise NotImplementedError

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a JSON-RPC message."""
        if self._closed:
            raise TransportClosedError("Transport is closed")
        raise NotImplementedError

    async def close(self) -> None:
        """Close the transport."""
        if self._closed:
            return
        self._closed = True
        if self.onclose:
            self.onclose()

    @property
    def closed(self) -> bool:
        return self._closed


class StdioTransport(Transport):
    """
    Stdio transport for MCP communication.
    Communicates with MCP server via stdin/stdout.
    """

    def __init__(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._process: Optional[Any] = None
        self._stdout_task: Optional[asyncio.Task] = None
        self._stderr_buffer: Optional[bytes] = None

    @property
    def stderr(self) -> Optional[bytes]:
        """Get accumulated stderr output."""
        return self._stderr_buffer

    async def start(self) -> None:
        """Start the stdio transport by spawning the process."""
        logger.debug(f"Starting stdio transport: {self.command} {' '.join(self.args)}")

        import subprocess
        self._process = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
        )

        self._stdout_task = asyncio.create_task(self._read_stdout())

    async def _read_stdout(self) -> None:
        """Read messages from stdout."""
        if not self._process or not self._process.stdout:
            return

        try:
            while not self._closed:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self._process.stdout.readline
                )
                if not line:
                    break
                try:
                    message = json.loads(line.decode("utf-8"))
                    if self.onmessage:
                        self.onmessage(message)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON message: {line}")
        except Exception as e:
            if not self._closed:
                logger.error(f"Error reading stdout: {e}")
                if self.onerror:
                    self.onerror(e)

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a JSON-RPC message via stdin."""
        if self._closed:
            raise TransportClosedError("Transport is closed")
        if not self._process or not self._process.stdin:
            raise TransportClosedError("Process stdin not available")

        content = json.dumps(message) + "\n"
        self._process.stdin.write(content.encode("utf-8"))
        self._process.stdin.flush()

    async def close(self) -> None:
        """Close the transport and terminate the process."""
        if self._closed:
            return

        self._closed = True

        if self._stdout_task:
            self._stdout_task.cancel()

        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()

        if self.onclose:
            self.onclose()


class SSITransport(Transport):
    """
    Server-Sent Events transport for MCP communication.
    Uses HTTP GET for server-sent events and POST for sending messages.
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth_provider: Optional[Any] = None,
    ):
        super().__init__()
        self.url = url
        self.headers = headers or {}
        self.auth_provider = auth_provider
        self._session: Optional[Any] = None

    async def start(self) -> None:
        """Start the SSE transport."""
        import httpx
        logger.debug(f"Starting SSE transport: {self.url}")
        self._session = httpx.AsyncClient(timeout=30.0)
        asyncio.create_task(self._listen_sse())

    async def _listen_sse(self) -> None:
        """Listen for SSE events from the server."""
        if not self._session:
            return
        try:
            async with self._session.stream("GET", self.url, headers=self.headers) as response:
                async for line in response.aiter_lines():
                    if self._closed:
                        break
                    if line.startswith("data: "):
                        data = line[6:]
                        if data and data != "[DONE]":
                            try:
                                message = json.loads(data)
                                if self.onmessage:
                                    self.onmessage(message)
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            if not self._closed and self.onerror:
                self.onerror(e)

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a JSON-RPC message via HTTP POST."""
        if self._closed:
            raise TransportClosedError("Transport is closed")
        if not self._session:
            raise TransportClosedError("Session not initialized")
        content = json.dumps(message)
        headers = {**self.headers, "Content-Type": "application/json"}
        response = await self._session.post(self.url, content=content, headers=headers)
        response.raise_for_status()

    async def close(self) -> None:
        """Close the SSE transport."""
        if self._closed:
            return
        self._closed = True
        if self.onclose:
            self.onclose()


class HTTPTransport(Transport):
    """
    HTTP transport for MCP Streamable HTTP communication.
    Uses POST for sending messages and GET for receiving.
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth_provider: Optional[Any] = None,
    ):
        super().__init__()
        self.url = url
        self.headers = headers or {}
        self.auth_provider = auth_provider
        self._session: Optional[Any] = None

    async def start(self) -> None:
        """Start the HTTP transport."""
        import httpx
        logger.debug(f"Starting HTTP transport: {self.url}")
        self._session = httpx.AsyncClient(timeout=60.0)

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a JSON-RPC message via HTTP POST."""
        if self._closed:
            raise TransportClosedError("Transport is closed")
        if not self._session:
            raise TransportClosedError("Session not initialized")
        content = json.dumps(message)
        headers = {**self.headers, "Content-Type": "application/json"}
        response = await self._session.post(self.url, content=content, headers=headers)
        response.raise_for_status()
        if response.status_code == 200 and self.onmessage:
            try:
                data = response.json()
                self.onmessage(data)
            except Exception:
                pass

    async def close(self) -> None:
        """Close the HTTP transport."""
        if self._closed:
            return
        self._closed = True
        if self.onclose:
            self.onclose()


class WebSocketTransport(Transport):
    """
    WebSocket transport for MCP communication.
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        self.url = url
        self.headers = headers or {}
        self._ws: Optional[Any] = None

    async def start(self) -> None:
        """Start the WebSocket transport."""
        import websockets
        logger.debug(f"Starting WebSocket transport: {self.url}")
        self._ws = await websockets.connect(self.url, extra_headers=self.headers)
        asyncio.create_task(self._listen_ws())

    async def _listen_ws(self) -> None:
        """Listen for WebSocket messages."""
        import websockets
        if not self._ws:
            return
        try:
            async for message in self._ws:
                if self._closed:
                    break
                if self.onmessage:
                    try:
                        data = json.loads(message)
                        self.onmessage(data)
                    except json.JSONDecodeError:
                        pass
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            if not self._closed and self.onerror:
                self.onerror(e)

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a JSON-RPC message via WebSocket."""
        if self._closed:
            raise TransportClosedError("Transport is closed")
        if not self._ws:
            raise TransportClosedError("WebSocket not connected")
        content = json.dumps(message)
        await self._ws.send(content)

    async def close(self) -> None:
        """Close the WebSocket transport."""
        if self._closed:
            return
        self._closed = True
        if self._ws:
            await self._ws.close()
        if self.onclose:
            self.onclose()


class InProcessTransport(Transport):
    """
    In-process linked transport pair for running MCP server and client
    in the same process without spawning a subprocess.

    Messages sent on one transport are delivered to the other's onmessage.
    Closing one transport closes the other.
    """

    def __init__(self):
        super().__init__()
        self._peer: Optional["InProcessTransport"] = None

    def _set_peer(self, peer: "InProcessTransport") -> None:
        """Set the peer transport for message delivery."""
        self._peer = peer

    async def start(self) -> None:
        """Start the transport (no-op for in-process)."""
        pass

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message to the peer transport."""
        if self._closed:
            raise TransportClosedError("Transport is closed")
        if not self._peer:
            raise TransportClosedError("No peer transport connected")

        asyncio.get_event_loop().call_soon(
            lambda: self._peer.onmessage and self._peer.onmessage(message)
        )

    async def close(self) -> None:
        """Close the transport and notify peer."""
        if self._closed:
            return
        self._closed = True
        self.onclose()
        if self._peer and not self._peer._closed:
            self._peer._closed = True
            self._peer.onclose()


def create_linked_transport_pair() -> tuple:
    """
    Create a pair of linked transports for in-process MCP communication.

    Returns:
        Tuple of (client_transport, server_transport)
    """
    client_transport = InProcessTransport()
    server_transport = InProcessTransport()
    client_transport._set_peer(server_transport)
    server_transport._set_peer(client_transport)
    return client_transport, server_transport


class SdkControlClientTransport(Transport):
    """
    SDK control transport for CLI-side MCP communication.

    Used to bridge communication between CLI's MCP Client and SDK process
    where the actual MCP server runs.
    """

    def __init__(
        self,
        server_name: str,
        send_mcp_message: Callable[[str, Dict[str, Any]], Any],
    ):
        super().__init__()
        self.server_name = server_name
        self.send_mcp_message = send_mcp_message

    async def start(self) -> None:
        """Start the transport (no-op)."""
        pass

    async def send(self, message: Dict[str, Any]) -> None:
        """Send message and wait for response via callback."""
        if self._closed:
            raise TransportClosedError("Transport is closed")

        response = await self.send_mcp_message(self.server_name, message)

        if self.onmessage:
            self.onmessage(response)

    async def close(self) -> None:
        """Close the transport."""
        if self._closed:
            return
        self._closed = True
        if self.onclose:
            self.onclose()


class SdkControlServerTransport(Transport):
    """
    SDK control transport for SDK-side MCP communication.

    Used in SDK process to bridge communication between control requests
    from CLI and the MCP server.
    """

    def __init__(
        self,
        send_mcp_message: Callable[[Dict[str, Any]], None],
    ):
        super().__init__()
        self.send_mcp_message = send_mcp_message

    async def start(self) -> None:
        """Start the transport (no-op)."""
        pass

    async def send(self, message: Dict[str, Any]) -> None:
        """Send response back via callback."""
        if self._closed:
            raise TransportClosedError("Transport is closed")
        self.send_mcp_message(message)

    async def close(self) -> None:
        """Close the transport."""
        if self._closed:
            return
        self._closed = True
        if self.onclose:
            self.onclose()
