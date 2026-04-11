"""MCP client implementation for api_server - complete implementation."""

import asyncio
import hashlib
import json
import logging
import os
import signal
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

logger = logging.getLogger(__name__)


# Constants
DEFAULT_MCP_TOOL_TIMEOUT_MS = 100_000_000
MCP_REQUEST_TIMEOUT_MS = 60000
MCP_CONNECTION_TIMEOUT_MS = 30000
MCP_AUTH_CACHE_TTL_MS = 15 * 60 * 1000
MAX_ERRORS_BEFORE_RECONNECT = 3
MAX_MCP_DESCRIPTION_LENGTH = 2048
MCP_STREAMABLE_HTTP_ACCEPT = "application/json, text/event-stream"
MCP_PROTOCOL_VERSION = "2025-03-26"


# Error Classes

class McpAuthError(Exception):
    """Raised when MCP tool call fails due to auth issues."""
    def __init__(self, server_name: str, message: str):
        super().__init__(message)
        self.name = "McpAuthError"
        self.server_name = server_name


class McpSessionExpiredError(Exception):
    """Raised when MCP session has expired and connection cache cleared."""
    def __init__(self, server_name: str):
        super().__init__(f'MCP server "{server_name}" session expired')
        self.name = "McpSessionExpiredError"
        self.server_name = server_name


class McpToolCallError(Exception):
    """Raised when MCP tool returns isError: true."""
    def __init__(
        self,
        message: str,
        telemetry_message: str,
        mcp_meta: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.name = "McpToolCallError"
        self.telemetry_message = telemetry_message
        self.mcp_meta = mcp_meta


class TransportClosedError(Exception):
    """Raised when transport is closed."""
    pass


class McpError(Exception):
    """Base MCP error."""
    def __init__(self, message: str, code: int = -32000):
        super().__init__(message)
        self.code = code
        self.message = message


# Terminal connection errors for reconnection logic
_TERMINAL_CONNECTION_ERRORS = [
    "ECONNRESET",
    "ETIMEDOUT",
    "EPIPE",
    "EHOSTUNREACH",
    "ECONNREFUSED",
    "Body Timeout Error",
    "terminated",
    "SSE stream disconnected",
    "Failed to reconnect SSE stream",
    "Maximum reconnection attempts",
]


def is_mcp_session_expired_error(error: Exception) -> bool:
    """Detect MCP session expired error (HTTP 404 + JSON-RPC code -32001)."""
    if hasattr(error, "code") and getattr(error, "code", None) == 404:
        error_msg = str(error)
        return '"code":-32001' in error_msg or '"code": -32001' in error_msg
    return False


def _is_terminal_connection_error(message: str) -> bool:
    """Check if error message indicates terminal connection failure."""
    return any(err in message for err in _TERMINAL_CONNECTION_ERRORS)


def _is_error_response(result: Any) -> bool:
    """Check if tool result indicates an error."""
    if isinstance(result, dict):
        return result.get("isError", False) or result.get("error") is not None
    return False


# Configuration getters

def get_mcp_tool_timeout_ms() -> int:
    """Get timeout for MCP tool calls in milliseconds."""
    env_timeout = os.environ.get("MCP_TOOL_TIMEOUT")
    if env_timeout:
        try:
            return int(env_timeout)
        except ValueError:
            pass
    return DEFAULT_MCP_TOOL_TIMEOUT_MS


def get_connection_timeout_ms() -> int:
    """Get connection timeout in milliseconds."""
    env_timeout = os.environ.get("MCP_TIMEOUT")
    if env_timeout:
        try:
            return int(env_timeout)
        except ValueError:
            pass
    return MCP_CONNECTION_TIMEOUT_MS


def get_mcp_server_connection_batch_size() -> int:
    """Get batch size for local MCP server connections."""
    env_size = os.environ.get("MCP_SERVER_CONNECTION_BATCH_SIZE")
    if env_size:
        try:
            return int(env_size)
        except ValueError:
            pass
    return 3


def get_remote_mcp_server_connection_batch_size() -> int:
    """Get batch size for remote MCP server connections."""
    env_size = os.environ.get("MCP_REMOTE_SERVER_CONNECTION_BATCH_SIZE")
    if env_size:
        try:
            return int(env_size)
        except ValueError:
            pass
    return 20


def is_local_mcp_server(config: "ScopedMcpServerConfig") -> bool:
    """Check if server config represents a local (stdio/sdk) server."""
    server_type = config.get("type") if isinstance(config, dict) else getattr(config, "type", None)
    return not server_type or server_type in ("stdio", "sdk")


def get_server_cache_key(name: str, server_ref: "ScopedMcpServerConfig") -> str:
    """Generate cache key for server connection."""
    if isinstance(server_ref, dict):
        ref_str = json.dumps(server_ref, sort_keys=True)
    else:
        ref_str = str(server_ref)
    return f"{name}-{ref_str}"


# Auth Cache (file-based for persistence)

_auth_cache_data: Optional[Dict[str, Any]] = None
_auth_cache_promise: Optional[Any] = None


def _get_mcp_auth_cache_path() -> str:
    """Get path for auth cache file."""
    claude_config_home = os.environ.get("CLAUDE_CONFIG_DIR", "")
    if not claude_config_home:
        return "/tmp/mcp-needs-auth-cache.json"
    return os.path.join(claude_config_home, "mcp-needs-auth-cache.json")


async def _read_mcp_auth_cache() -> Dict[str, Any]:
    """Read auth cache from disk."""
    global _auth_cache_data, _auth_cache_promise

    if _auth_cache_promise is None:
        async def _do_read():
            cache_path = _get_mcp_auth_cache_path()
            try:
                if os.path.exists(cache_path):
                    with open(cache_path, "r") as f:
                        return json.load(f)
            except Exception:
                pass
            return {}

        _auth_cache_promise = _do_read()
        _auth_cache_data = await _auth_cache_promise

    return _auth_cache_data or {}


async def is_mcp_auth_cached(server_id: str) -> bool:
    """Check if server is in auth cache and not expired."""
    cache = await _read_mcp_auth_cache()
    entry = cache.get(server_id)
    if not entry:
        return False
    return (time.time() * 1000) - entry.get("timestamp", 0) < MCP_AUTH_CACHE_TTL_MS


_write_chain = asyncio.ensure_future(asyncio.sleep(0))


def set_mcp_auth_cache_entry(server_id: str) -> None:
    """Set auth cache entry and persist to disk."""
    global _write_chain, _auth_cache_promise

    _write_chain = _write_chain.then(
        lambda: _do_write_cache(server_id),
        lambda e: None,  # Suppress errors
    )


async def _do_write_cache(server_id: str) -> None:
    """Write auth cache entry to disk."""
    global _auth_cache_data, _auth_cache_promise

    cache = await _read_mcp_auth_cache()
    cache[server_id] = {"timestamp": time.time() * 1000}

    cache_path = _get_mcp_auth_cache_path()
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(cache, f)
        _auth_cache_promise = None  # Invalidate read cache
    except Exception:
        pass


def clear_mcp_auth_cache() -> None:
    """Clear the auth cache."""
    global _auth_cache_data, _auth_cache_promise, _write_chain

    _auth_cache_data = None
    _auth_cache_promise = None
    _write_chain = asyncio.ensure_future(asyncio.sleep(0))

    cache_path = _get_mcp_auth_cache_path()
    try:
        if os.path.exists(cache_path):
            os.remove(cache_path)
    except Exception:
        pass


# Tool Result Cache

class ToolResultCache:
    """Cache tool results by content hash."""

    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._max_size = max_size
        self._access_times: Dict[str, float] = {}

    def _compute_hash(self, content: Any) -> str:
        """Compute hash for content."""
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def get(self, content: Any) -> Optional[Any]:
        """Get cached result for content."""
        content_hash = self._compute_hash(content)
        entry = self._cache.get(content_hash)
        if entry:
            self._access_times[content_hash] = time.time()
            return entry[0]
        return None

    def set(self, content: Any, result: Any) -> None:
        """Cache result for content."""
        if len(self._cache) >= self._max_size:
            # Evict least recently used
            oldest_hash = min(self._access_times, key=self._access_times.get)
            self._cache.pop(oldest_hash, None)
            self._access_times.pop(oldest_hash, None)

        content_hash = self._compute_hash(content)
        self._cache[content_hash] = (result, time.time())
        self._access_times[content_hash] = time.time()

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        self._access_times.clear()


# Global tool result cache
_tool_result_cache = ToolResultCache()


# Connection Cache

_connection_cache: Dict[str, Any] = {}


def get_connection_cache(name: str, server_ref: "ScopedMcpServerConfig") -> Optional[Any]:
    """Get cached connection for server."""
    key = get_server_cache_key(name, server_ref)
    return _connection_cache.get(key)


def set_connection_cache(name: str, server_ref: "ScopedMcpServerConfig", client: Any) -> None:
    """Cache connection for server."""
    key = get_server_cache_key(name, server_ref)
    _connection_cache[key] = client


async def clear_server_cache(name: str, server_ref: "ScopedMcpServerConfig") -> None:
    """Clear cached connection and related caches."""
    key = get_server_cache_key(name, server_ref)

    cached = _connection_cache.get(key)
    if cached and hasattr(cached, "cleanup"):
        try:
            cleanup = cached.cleanup
            if asyncio.iscoroutinefunction(cleanup):
                await cleanup()
            else:
                cleanup()
        except Exception as e:
            logger.debug(f"Error during cleanup: {e}")

    _connection_cache.pop(key, None)
    _fetch_tools_cache.pop(name, None)
    _fetch_resources_cache.pop(name, None)
    _fetch_prompts_cache.pop(name, None)


# Fetch Caches

_fetch_tools_cache: Dict[str, Any] = {}
_fetch_resources_cache: Dict[str, Any] = {}
_fetch_prompts_cache: Dict[str, Any] = {}
MCP_FETCH_CACHE_SIZE = 20


def _evict_oldest_cache(cache: Dict[str, Any]) -> None:
    """Evict oldest entry from cache when full."""
    if len(cache) >= MCP_FETCH_CACHE_SIZE:
        oldest_key = next(iter(cache))
        cache.pop(oldest_key, None)


# Server Capabilities

@dataclass
class ServerCapabilities:
    """MCP server capabilities."""
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    elicitation: Optional[Dict[str, Any]] = None


@dataclass
class ServerInfo:
    """Server information."""
    name: Optional[str] = None
    version: Optional[str] = None


# Transport Interface

class MCPTransport(ABC):
    """Abstract base class for MCP transports."""

    @abstractmethod
    async def start(self) -> None:
        """Start the transport."""
        pass

    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> None:
        """Send a JSON-RPC message."""
        pass

    @abstractmethod
    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Receive messages as an async iterator."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the transport."""
        pass


class StdioTransport(MCPTransport):
    """Process-based transport using stdin/stdout."""

    def __init__(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
    ):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.stderr_callback = stderr_callback
        self._process: Optional[Any] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._closed = False
        self._message_queue: Optional[asyncio.Queue] = None
        self.onclose: Optional[Callable[[], None]] = None
        self.onerror: Optional[Callable[[Exception], None]] = None

    @property
    def closed(self) -> bool:
        return self._closed

    async def start(self) -> None:
        """Start the stdio transport by spawning the process."""
        import subprocess

        self._message_queue = asyncio.Queue()

        self._process = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
        )

        self._reader_task = asyncio.create_task(self._read_stdout())

    async def _read_stdout(self) -> None:
        """Read messages from stdout."""
        if not self._process or not self._process.stdout:
            return

        loop = asyncio.get_event_loop()

        try:
            while not self._closed:
                line = await loop.run_in_executor(
                    None, self._process.stdout.readline
                )
                if not line:
                    break
                try:
                    message = json.loads(line.decode("utf-8"))
                    if self._message_queue:
                        await self._message_queue.put(message)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON message: {line}")
        except Exception as e:
            if not self._closed and self.onerror:
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

    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Receive messages from the queue."""
        if not self._message_queue:
            raise TransportClosedError("Message queue not initialized")

        while not self._closed:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                yield message
            except asyncio.TimeoutError:
                continue

    async def close(self) -> None:
        """Close the transport and terminate the process."""
        if self._closed:
            return

        self._closed = True

        if self._reader_task:
            self._reader_task.cancel()

        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()

            # Read stderr
            if self._process.stderr:
                try:
                    stderr_output = self._process.stderr.read()
                    if stderr_output and self.stderr_callback:
                        self.stderr_callback(stderr_output.decode("utf-8", errors="replace"))
                except Exception:
                    pass

        if self.onclose:
            self.onclose()


class SSETransport(MCPTransport):
    """Server-Sent Events transport over HTTP."""

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth_provider: Optional[Any] = None,
        event_source_factory: Optional[Callable] = None,
    ):
        self.url = url
        self.headers = headers or {}
        self.auth_provider = auth_provider
        self.event_source_factory = event_source_factory
        self._session: Optional[Any] = None
        self._closed = False
        self._message_queue: Optional[asyncio.Queue] = None
        self._reader_task: Optional[asyncio.Task] = None
        self.onclose: Optional[Callable[[], None]] = None
        self.onerror: Optional[Callable[[Exception], None]] = None

    @property
    def closed(self) -> bool:
        return self._closed

    async def start(self) -> None:
        """Start the SSE transport."""
        import httpx

        self._message_queue = asyncio.Queue()
        self._session = httpx.AsyncClient(timeout=30.0)
        self._reader_task = asyncio.create_task(self._listen_sse())

    async def _listen_sse(self) -> None:
        """Listen for SSE events from the server."""
        if not self._session:
            return

        # Build headers with auth if provider available
        headers = dict(self.headers)
        if self.auth_provider:
            tokens = await self.auth_provider.tokens()
            if tokens and tokens.access_token:
                headers["Authorization"] = f"Bearer {tokens.access_token}"

        try:
            async with self._session.stream("GET", self.url, headers=headers) as response:
                async for line in response.aiter_lines():
                    if self._closed:
                        break
                    if line.startswith("data: "):
                        data = line[6:]
                        if data and data != "[DONE]":
                            try:
                                message = json.loads(data)
                                if self._message_queue:
                                    await self._message_queue.put(message)
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

        # Build headers with auth if provider available
        headers = dict(self.headers)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = MCP_STREAMABLE_HTTP_ACCEPT

        if self.auth_provider:
            tokens = await self.auth_provider.tokens()
            if tokens and tokens.access_token:
                headers["Authorization"] = f"Bearer {tokens.access_token}"

        response = await self._session.post(self.url, json=message, headers=headers)
        response.raise_for_status()

    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Receive messages from the queue."""
        if not self._message_queue:
            raise TransportClosedError("Message queue not initialized")

        while not self._closed:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                yield message
            except asyncio.TimeoutError:
                continue

    async def close(self) -> None:
        """Close the SSE transport."""
        if self._closed:
            return

        self._closed = True

        if self._reader_task:
            self._reader_task.cancel()

        if self._session:
            await self._session.aclose()

        if self.onclose:
            self.onclose()


class HTTPTransport(MCPTransport):
    """HTTP Streamable transport for MCP communication."""

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth_provider: Optional[Any] = None,
        session_id: Optional[str] = None,
    ):
        self.url = url
        self.headers = headers or {}
        self.auth_provider = auth_provider
        self.session_id = session_id
        self._session: Optional[Any] = None
        self._closed = False
        self._message_queue: Optional[asyncio.Queue] = None
        self._reader_task: Optional[asyncio.Task] = None
        self.onclose: Optional[Callable[[], None]] = None
        self.onerror: Optional[Callable[[Exception], None]] = None

    @property
    def closed(self) -> bool:
        return self._closed

    async def start(self) -> None:
        """Start the HTTP transport."""
        import httpx

        self._message_queue = asyncio.Queue()
        self._session = httpx.AsyncClient(timeout=60.0)
        self._reader_task = asyncio.create_task(self._listen_get())

    async def _listen_get(self) -> None:
        """Listen for messages via HTTP GET (SSE)."""
        if not self._session:
            return

        # Build headers with auth if provider available
        headers = dict(self.headers)
        headers["Accept"] = "text/event-stream"

        if self.session_id:
            headers["X-Mcp-Session-Id"] = self.session_id

        if self.auth_provider:
            tokens = await self.auth_provider.tokens()
            if tokens and tokens.access_token:
                headers["Authorization"] = f"Bearer {tokens.access_token}"

        try:
            async with self._session.stream("GET", self.url, headers=headers) as response:
                async for line in response.aiter_lines():
                    if self._closed:
                        break
                    if line.startswith("data: "):
                        data = line[6:]
                        if data and data != "[DONE]":
                            try:
                                message = json.loads(data)
                                if self._message_queue:
                                    await self._message_queue.put(message)
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

        # Build headers with auth if provider available
        headers = dict(self.headers)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = MCP_STREAMABLE_HTTP_ACCEPT

        if self.session_id:
            headers["X-Mcp-Session-Id"] = self.session_id

        if self.auth_provider:
            tokens = await self.auth_provider.tokens()
            if tokens and tokens.access_token:
                headers["Authorization"] = f"Bearer {tokens.access_token}"

        response = await self._session.post(self.url, json=message, headers=headers)
        response.raise_for_status()

        # Handle response
        if response.status_code == 200:
            try:
                data = response.json()
                if self._message_queue:
                    await self._message_queue.put(data)
            except Exception:
                pass

    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Receive messages from the queue."""
        if not self._message_queue:
            raise TransportClosedError("Message queue not initialized")

        while not self._closed:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                yield message
            except asyncio.TimeoutError:
                continue

    async def close(self) -> None:
        """Close the HTTP transport."""
        if self._closed:
            return

        self._closed = True

        if self._reader_task:
            self._reader_task.cancel()

        if self._session:
            await self._session.aclose()

        if self.onclose:
            self.onclose()


class WebSocketTransport(MCPTransport):
    """WebSocket transport for MCP communication."""

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth_token: Optional[str] = None,
        tls_options: Optional[Dict[str, Any]] = None,
    ):
        self.url = url
        self.headers = headers or {}
        self.auth_token = auth_token
        self.tls_options = tls_options
        self._ws: Optional[Any] = None
        self._closed = False
        self._message_queue: Optional[asyncio.Queue] = None
        self._reader_task: Optional[asyncio.Task] = None
        self.onclose: Optional[Callable[[], None]] = None
        self.onerror: Optional[Callable[[Exception], None]] = None

    @property
    def closed(self) -> bool:
        return self._closed

    async def start(self) -> None:
        """Start the WebSocket transport."""
        import websockets

        self._message_queue = asyncio.Queue()

        # Build headers
        headers = dict(self.headers)
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        self._ws = await websockets.connect(
            self.url,
            extra_headers=headers,
            ssl=self.tls_options,
        )
        self._reader_task = asyncio.create_task(self._listen_ws())

    async def _listen_ws(self) -> None:
        """Listen for WebSocket messages."""
        import websockets

        if not self._ws:
            return

        try:
            async for message in self._ws:
                if self._closed:
                    break
                if self._message_queue:
                    try:
                        data = json.loads(message)
                        await self._message_queue.put(data)
                    except json.JSONDecodeError:
                        pass
        except websockets.exceptions.ConnectionClosed:
            if not self._closed and self.onerror:
                self.onerror(Exception("WebSocket connection closed"))
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

    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Receive messages from the queue."""
        if not self._message_queue:
            raise TransportClosedError("Message queue not initialized")

        while not self._closed:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                yield message
            except asyncio.TimeoutError:
                continue

    async def close(self) -> None:
        """Close the WebSocket transport."""
        if self._closed:
            return

        self._closed = True

        if self._reader_task:
            self._reader_task.cancel()

        if self._ws:
            await self._ws.close()

        if self.onclose:
            self.onclose()


# MCP Client

@dataclass
class MCPClient:
    """MCP client for communicating with servers."""
    name: str
    config: "ScopedMcpServerConfig"
    transport: Optional[MCPTransport] = None
    capabilities: Optional[ServerCapabilities] = None
    server_info: Optional[ServerInfo] = None
    instructions: Optional[str] = None
    cleanup_fn: Optional[Callable[[], Any]] = None

    _request_id: int = field(default=0)
    _pending_requests: Dict[int, asyncio.Future] = field(default_factory=dict)
    _closed: bool = field(default=False)
    _connection_start_time: float = field(default_factory=time.time)
    _consecutive_errors: int = field(default=0)

    def __post_init__(self):
        if isinstance(self.config, dict):
            self.name = self.config.get("name") or self.name
        else:
            self.name = getattr(self.config, "name", None) or self.name

    def get_next_request_id(self) -> int:
        """Get next unique request ID."""
        self._request_id += 1
        return self._request_id

    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Send JSON-RPC request and wait for response."""
        if self._closed:
            raise TransportClosedError("Client is closed")

        request_id = self.get_next_request_id()
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params:
            message["params"] = params

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            if self.transport:
                await self.transport.send(message)
            timeout_ms = get_mcp_tool_timeout_ms()
            result = await asyncio.wait_for(future, timeout=timeout_ms / 1000)
            return result
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise
        except Exception:
            self._pending_requests.pop(request_id, None)
            raise

    async def send_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send JSON-RPC notification (no response expected)."""
        if self._closed:
            raise TransportClosedError("Client is closed")

        message = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            message["params"] = params

        if self.transport:
            await self.transport.send(message)

    def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming JSON-RPC message."""
        # Handle response
        if "id" in message:
            request_id = message["id"]
            future = self._pending_requests.pop(request_id, None)

            if future:
                if "error" in message:
                    future.set_exception(
                        McpError(
                            message.get("error", {}).get("message", "Unknown error"),
                            code=message.get("error", {}).get("code", -32000),
                        )
                    )
                elif "result" in message:
                    future.set_result(message["result"])
            return

        # Handle server-side request (e.g., notifications)
        method = message.get("method")
        if method and self._request_handler:
            params = message.get("params", {})
            asyncio.create_task(self._request_handler(method, params))

    def _handle_error(self, error: Exception) -> None:
        """Handle transport error."""
        self._consecutive_errors += 1

        error_msg = str(error)
        logger.debug(f"Connection error for '{self.name}': {error_msg}")

        server_type = (
            self.config.get("type")
            if isinstance(self.config, dict)
            else getattr(self.config, "type", None)
        )

        # Handle session expiry for HTTP transports
        if server_type in ("http", "claudeai-proxy") and is_mcp_session_expired_error(error):
            logger.debug(f"MCP session expired for '{self.name}', triggering reconnection")
            asyncio.create_task(self.close())
            return

        # Handle terminal connection errors
        if server_type in ("sse", "http", "claudeai-proxy"):
            if _is_terminal_connection_error(error_msg):
                if self._consecutive_errors >= MAX_ERRORS_BEFORE_RECONNECT:
                    logger.debug(
                        f"Max consecutive errors reached for '{self.name}', closing connection"
                    )
                    self._consecutive_errors = 0
                    asyncio.create_task(self.close())
                return
            else:
                self._consecutive_errors = 0

    def _handle_close(self) -> None:
        """Handle transport close."""
        self._closed = True

        key = get_server_cache_key(self.name, self.config)
        _connection_cache.pop(key, None)
        _fetch_tools_cache.pop(self.name, None)
        _fetch_resources_cache.pop(self.name, None)
        _fetch_prompts_cache.pop(self.name, None)

        logger.debug(f"Connection closed for '{self.name}', caches cleared")

    async def close(self) -> None:
        """Close the client and transport."""
        if self._closed:
            return

        self._closed = True

        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()

        self._pending_requests.clear()

        if self.transport:
            await self.transport.close()

        if self.cleanup_fn:
            try:
                result = self.cleanup_fn()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")

        self._handle_close()

    def set_request_handler(self, method: str, handler: Callable) -> None:
        """Set handler for server-initiated requests."""
        if not hasattr(self, "_request_handlers"):
            self._request_handlers: Dict[str, Callable] = {}
        self._request_handlers[method] = handler

    @property
    def _request_handler(self) -> Optional[Callable]:
        """Get generic request handler."""
        return getattr(self, "_request_handler_fn", None)

    @_request_handler.setter
    def _request_handler(self, handler: Callable) -> None:
        self._request_handler_fn = handler


# Scoped Config Type

class ScopedMcpServerConfig(dict):
    """MCP server configuration with scope information."""

    def __init__(
        self,
        scope: Optional[str] = None,
        type: Optional[str] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        oauth: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.scope = scope
        self.type = type
        self.command = command
        self.args = args
        self.env = env
        self.url = url
        self.headers = headers
        self.name = name
        self.id = id
        self.oauth = oauth

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by key."""
        if hasattr(self, key):
            return getattr(self, key)
        return super().get(key, default)


# Connection Result Types

@dataclass
class ConnectedMCPServer:
    """Successfully connected MCP server."""
    client: MCPClient
    name: str
    type: str = "connected"
    capabilities: Optional[ServerCapabilities] = None
    server_info: Optional[Dict[str, str]] = None
    instructions: Optional[str] = None
    config: Optional[ScopedMcpServerConfig] = None
    cleanup: Optional[Callable[[], Any]] = None


@dataclass
class FailedMCPServer:
    """Failed MCP server connection."""
    name: str
    type: str = "failed"
    config: Optional[ScopedMcpServerConfig] = None
    error: Optional[str] = None


@dataclass
class NeedsAuthMCPServer:
    """MCP server requiring authentication."""
    name: str
    type: str = "needs-auth"
    config: Optional[ScopedMcpServerConfig] = None


@dataclass
class PendingMCPServer:
    """Pending MCP server connection."""
    name: str
    type: str = "pending"
    config: Optional[ScopedMcpServerConfig] = None
    reconnect_attempt: Optional[int] = None
    max_reconnect_attempts: Optional[int] = None


# Transport Factory Functions

async def create_stdio_transport(config: ScopedMcpServerConfig) -> StdioTransport:
    """Create stdio transport from config."""
    if isinstance(config, dict):
        command = config.get("command", "")
        args = config.get("args", [])
        env = config.get("env", {})
    else:
        command = getattr(config, "command", "") or ""
        args = getattr(config, "args", []) or []
        env = getattr(config, "env", {}) or {}

    return StdioTransport(
        command=command,
        args=args,
        env=env,
    )


async def create_sse_transport(config: ScopedMcpServerConfig) -> SSETransport:
    """Create SSE transport from config."""
    if isinstance(config, dict):
        url = config.get("url", "")
        headers = config.get("headers", {})
        oauth = config.get("oauth")
    else:
        url = getattr(config, "url", "") or ""
        headers = getattr(config, "headers", {}) or {}
        oauth = getattr(config, "oauth", None)

    auth_provider = None
    if oauth:
        from .auth import MCPAuthProvider

        auth_provider = MCPAuthProvider(
            server_name=config.get("name", "") if isinstance(config, dict) else getattr(config, "name", ""),
            server_config=config if isinstance(config, dict) else {},
        )

    return SSETransport(
        url=url,
        headers=headers,
        auth_provider=auth_provider,
    )


async def create_http_transport(config: ScopedMcpServerConfig) -> HTTPTransport:
    """Create HTTP transport from config."""
    if isinstance(config, dict):
        url = config.get("url", "")
        headers = config.get("headers", {})
        oauth = config.get("oauth")
    else:
        url = getattr(config, "url", "") or ""
        headers = getattr(config, "headers", {}) or {}
        oauth = getattr(config, "oauth", None)

    auth_provider = None
    if oauth:
        from .auth import MCPAuthProvider

        auth_provider = MCPAuthProvider(
            server_name=config.get("name", "") if isinstance(config, dict) else getattr(config, "name", ""),
            server_config=config if isinstance(config, dict) else {},
        )

    return HTTPTransport(
        url=url,
        headers=headers,
        auth_provider=auth_provider,
    )


async def create_websocket_transport(config: ScopedMcpServerConfig) -> WebSocketTransport:
    """Create WebSocket transport from config."""
    if isinstance(config, dict):
        url = config.get("url", "")
        headers = config.get("headers", {})
        auth_token = config.get("auth_token")
    else:
        url = getattr(config, "url", "") or ""
        headers = getattr(config, "headers", {}) or {}
        auth_token = getattr(config, "auth_token", None)

    return WebSocketTransport(
        url=url,
        headers=headers,
        auth_token=auth_token,
    )


async def create_transport_for_config(config: ScopedMcpServerConfig) -> MCPTransport:
    """Create appropriate transport for config."""
    config_type = (
        config.get("type")
        if isinstance(config, dict)
        else getattr(config, "type", None)
    )

    if config_type is None or config_type == "stdio":
        return await create_stdio_transport(config)
    elif config_type in ("sse", "sse-ide"):
        return await create_sse_transport(config)
    elif config_type in ("http", "claudeai-proxy"):
        return await create_http_transport(config)
    elif config_type in ("ws", "ws-ide"):
        return await create_websocket_transport(config)
    else:
        raise ValueError(f"Unsupported server type: {config_type}")


# Server Connection

async def connect_to_server(
    name: str,
    config: ScopedMcpServerConfig,
    server_stats: Optional[Dict[str, int]] = None,
) -> Union[ConnectedMCPServer, FailedMCPServer, NeedsAuthMCPServer, PendingMCPServer]:
    """Connect to a single MCP server."""
    server_name = (
        name
        or (config.get("name") if isinstance(config, dict) else getattr(config, "name", "unknown"))
    )
    start_time = time.time()

    config_type = (
        config.get("type")
        if isinstance(config, dict)
        else getattr(config, "type", None)
    )

    # Check auth cache for remote servers
    if config_type in ("http", "sse", "claudeai-proxy"):
        if await is_mcp_auth_cached(server_name):
            logger.debug(f"Skipping connection for '{server_name}' (cached needs-auth)")
            return NeedsAuthMCPServer(
                name=server_name,
                type="needs-auth",
                config=config,
            )

    stderr_output = ""

    try:
        transport = await create_transport_for_config(config)

        # Set up stderr callback for stdio transport
        if config_type in (None, "stdio"):
            stdio_transport = transport
            if isinstance(stdio_transport, StdioTransport):

                def stderr_callback(data: str) -> None:
                    nonlocal stderr_output
                    if len(stderr_output) < 64 * 1024 * 1024:  # 64MB cap
                        stderr_output += data

                stdio_transport.stderr_callback = stderr_callback

        client = MCPClient(
            name=server_name,
            config=config,
            transport=transport,
        )

        if transport.onerror is None:
            transport.onerror = client._handle_error
        if transport.onclose is None:
            transport.onclose = client._handle_close

        timeout_ms = get_connection_timeout_ms()

        try:
            await asyncio.wait_for(transport.start(), timeout=timeout_ms / 1000)
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(
                f"Transport start timed out for '{server_name}' after {elapsed:.1f}s"
            )
            await transport.close()
            return FailedMCPServer(
                name=server_name,
                type="failed",
                config=config,
                error=f"Connection timed out after {elapsed:.1f}s",
            )

        # Send initialize notification
        try:
            init_result = await client.send_request("initialize", {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "roots": {"list": {}},
                    "elicitation": {},
                },
                "clientInfo": {
                    "name": "api-server",
                    "version": "1.0.0",
                },
            })

            # Store server capabilities and info
            if init_result:
                server_capabilities = init_result.get("capabilities", {})
                client.capabilities = ServerCapabilities(
                    tools=server_capabilities.get("tools"),
                    resources=server_capabilities.get("resources"),
                    prompts=server_capabilities.get("prompts"),
                    logging=server_capabilities.get("logging"),
                    elicitation=server_capabilities.get("elicitation"),
                )
                client.server_info = ServerInfo(
                    name=init_result.get("serverInfo", {}).get("name"),
                    version=init_result.get("serverInfo", {}).get("version"),
                )

        except Exception as e:
            logger.warning(f"Initialize request failed: {e}")

        # Send initialized notification
        try:
            await client.send_notification("initialized", {})
        except Exception:
            pass

        # Log stderr output if any
        if stderr_output:
            logger.warning(f"Server stderr for '{server_name}': {stderr_output[:1000]}")

        elapsed = time.time() - start_time
        logger.info(f"Connected to MCP server '{server_name}' in {elapsed:.2f}s")

        # Set up cleanup function
        async def cleanup() -> None:
            server_type = (
                config.get("type")
                if isinstance(config, dict)
                else getattr(config, "type", None)
            )

            if server_type in (None, "stdio") and transport:
                stdio_transport = transport
                if isinstance(stdio_transport, StdioTransport) and stdio_transport._process:
                    child_pid = stdio_transport._process.pid
                    if child_pid:
                        try:
                            os.kill(child_pid, signal.SIGINT)
                            await asyncio.sleep(0.1)

                            try:
                                os.kill(child_pid, 0)
                                os.kill(child_pid, signal.SIGTERM)
                                await asyncio.sleep(0.4)

                                try:
                                    os.kill(child_pid, 0)
                                    os.kill(child_pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                            except ProcessLookupError:
                                pass
                        except Exception as e:
                            logger.debug(f"Error sending signals to MCP process: {e}")

            await client.close()

        result = ConnectedMCPServer(
            client=client,
            name=server_name,
            type="connected",
            capabilities=client.capabilities,
            server_info=client.server_info,
            instructions=client.instructions,
            config=config,
            cleanup=cleanup,
        )

        set_connection_cache(server_name, config, result)

        return result

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.error(f"Connection to '{server_name}' timed out after {elapsed:.1f}s")
        return FailedMCPServer(
            name=server_name,
            type="failed",
            config=config,
            error=f"Connection timed out after {elapsed:.1f}s",
        )

    except McpAuthError as e:
        logger.warning(f"Authentication required for '{server_name}': {e}")
        set_mcp_auth_cache_entry(server_name)
        return NeedsAuthMCPServer(
            name=server_name,
            type="needs-auth",
            config=config,
        )

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)

        # Check for auth failures
        if config_type in ("sse", "http", "claudeai-proxy"):
            if "401" in error_msg or "Unauthorized" in error_msg:
                logger.warning(f"Authentication required for '{server_name}': {e}")
                set_mcp_auth_cache_entry(server_name)
                return NeedsAuthMCPServer(
                    name=server_name,
                    type="needs-auth",
                    config=config,
                )

        logger.error(f"Failed to connect to '{server_name}' after {elapsed:.1f}s: {e}")
        return FailedMCPServer(
            name=server_name,
            type="failed",
            config=config,
            error=str(e),
        )


async def ensure_connected_client(
    client: ConnectedMCPServer,
) -> ConnectedMCPServer:
    """Ensure client is still connected, reconnecting if necessary."""
    config_type = (
        client.config.get("type")
        if isinstance(client.config, dict)
        else getattr(client.config, "type", None)
    )

    if config_type == "sdk":
        return client

    connected_client = await connect_to_server(client.name, client.config)
    if connected_client.type != "connected":
        raise Exception(f'MCP server "{client.name}" is not connected')
    return connected_client


async def start_client(
    name: str,
    config: ScopedMcpServerConfig,
) -> Union[ConnectedMCPServer, NeedsAuthMCPServer, FailedMCPServer]:
    """Start a client connection."""
    result = await connect_to_server(name, config)

    if result.type == "connected":
        return result
    elif result.type == "needs-auth":
        return result
    else:
        raise Exception(result.error or "Connection failed")


async def close_client(client: MCPClient) -> None:
    """Close a client connection."""
    await client.close()


# JSON-RPC Helpers

async def send_jsonrpc_request(
    client: MCPClient,
    method: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """Send JSON-RPC request."""
    return await client.send_request(method, params)


async def send_jsonrpc_notification(
    client: MCPClient,
    method: str,
    params: Optional[Dict[str, Any]] = None,
) -> None:
    """Send JSON-RPC notification."""
    await client.send_notification(method, params)


# Batch Processing

async def process_batched(
    items: List[Tuple[str, ScopedMcpServerConfig]],
    concurrency: int,
    processor: Callable[[Tuple[str, ScopedMcpServerConfig]], Any],
) -> None:
    """Process items in batches with concurrency limit."""
    semaphore = asyncio.Semaphore(concurrency)

    async def process_with_semaphore(
        item: Tuple[str, ScopedMcpServerConfig],
    ) -> None:
        async with semaphore:
            await processor(item)

    await asyncio.gather(
        *[process_with_semaphore(item) for item in items]
    )


async def connect_batch(
    configs: Dict[str, ScopedMcpServerConfig],
    on_connection_attempt: Callable[
        [Union[ConnectedMCPServer, FailedMCPServer, NeedsAuthMCPServer, PendingMCPServer], List[Any], List[Any]], None
    ],
) -> None:
    """Connect to multiple servers in batches."""
    local_servers: List[Tuple[str, ScopedMcpServerConfig]] = []
    remote_servers: List[Tuple[str, ScopedMcpServerConfig]] = []

    for server_name, config in configs.items():
        if is_local_mcp_server(config):
            local_servers.append((server_name, config))
        else:
            remote_servers.append((server_name, config))

    local_batch_size = get_mcp_server_connection_batch_size()
    remote_batch_size = get_remote_mcp_server_connection_batch_size()

    async def process_server(
        item: Tuple[str, ScopedMcpServerConfig],
    ) -> None:
        server_name, config = item
        try:
            client = await connect_to_server(server_name, config)

            if client.type != "connected":
                on_connection_attempt(client, [], [])
                return

            tools = await fetch_tools_for_client(client)
            prompts = await fetch_prompts_for_client(client)

            on_connection_attempt(client, tools, prompts)

        except Exception as e:
            logger.error(f"Error connecting to '{server_name}': {e}")
            on_connection_attempt(
                FailedMCPServer(
                    name=server_name,
                    type="failed",
                    config=config,
                    error=str(e),
                ),
                [],
                [],
            )

    await asyncio.gather(
        process_batched(local_servers, local_batch_size, process_server),
        process_batched(remote_servers, remote_batch_size, process_server),
    )


async def fetch_tools_for_client(
    client: Union[ConnectedMCPServer, FailedMCPServer, NeedsAuthMCPServer, PendingMCPServer],
) -> List[Any]:
    """Fetch tools from connected server."""
    if client.type != "connected":
        return []

    name = client.name

    if name in _fetch_tools_cache:
        return _fetch_tools_cache[name]

    _evict_oldest_cache(_fetch_tools_cache)

    try:
        tools_result = await client.client.send_request("tools/list")
        tools = tools_result.get("tools", []) if tools_result else []

        _fetch_tools_cache[name] = tools
        return tools

    except Exception as e:
        logger.error(f"Error fetching tools for '{name}': {e}")
        return []


async def fetch_prompts_for_client(
    client: Union[ConnectedMCPServer, FailedMCPServer, NeedsAuthMCPServer, PendingMCPServer],
) -> List[Any]:
    """Fetch prompts/commands from connected server."""
    if client.type != "connected":
        return []

    name = client.name

    if name in _fetch_prompts_cache:
        return _fetch_prompts_cache[name]

    _evict_oldest_cache(_fetch_prompts_cache)

    try:
        prompts_result = await client.client.send_request("prompts/list")
        prompts = prompts_result.get("prompts", []) if prompts_result else []

        _fetch_prompts_cache[name] = prompts
        return prompts

    except Exception as e:
        logger.error(f"Error fetching prompts for '{name}': {e}")
        return []


async def fetch_resources_for_client(
    client: Union[ConnectedMCPServer, FailedMCPServer, NeedsAuthMCPServer, PendingMCPServer],
) -> List[Any]:
    """Fetch resources from connected server."""
    if client.type != "connected":
        return []

    name = client.name

    if name in _fetch_resources_cache:
        return _fetch_resources_cache[name]

    _evict_oldest_cache(_fetch_resources_cache)

    try:
        resources_result = await client.client.send_request("resources/list")
        resources = resources_result.get("resources", []) if resources_result else []

        _fetch_resources_cache[name] = resources
        return resources

    except Exception as e:
        logger.error(f"Error fetching resources for '{name}': {e}")
        return []


# Tool Call with Caching

async def call_mcp_tool_with_cache(
    client: MCPClient,
    tool_name: str,
    tool_args: Dict[str, Any],
    cache_enabled: bool = True,
) -> Any:
    """Call MCP tool with optional content-based caching."""
    if cache_enabled:
        # Check cache first
        cache_key = {"tool": tool_name, "args": tool_args}
        cached_result = _tool_result_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for tool {tool_name}")
            return cached_result

    # Call the tool
    result = await client.send_request("tools/call", {
        "name": tool_name,
        "arguments": tool_args,
    })

    # Cache the result
    if cache_enabled and result is not None:
        _tool_result_cache.set(cache_key, result)

    return result


def clear_tool_result_cache() -> None:
    """Clear the tool result cache."""
    _tool_result_cache.clear()


# OAuth Token Refresh for claude.ai proxy

async def create_claudeai_proxy_fetch(
    inner_fetch: Callable,
) -> Callable:
    """Create fetch wrapper that handles OAuth token refresh for claude.ai proxy."""

    async def claudeai_proxy_fetch(
        url: str,
        init: Optional[Dict[str, Any]] = None,
    ) -> Any:
        from .auth import (
            check_and_refresh_oauth_token_if_needed,
            get_claudeai_oauth_tokens,
            handle_oauth_401_error,
        )

        async def do_request() -> Tuple[Any, str]:
            await check_and_refresh_oauth_token_if_needed()
            current_tokens = get_claudeai_oauth_tokens()

            if not current_tokens:
                raise Exception("No claude.ai OAuth token available")

            headers = dict(init.get("headers", {}) if init else {})
            headers["Authorization"] = f"Bearer {current_tokens.access_token}"

            response = await inner_fetch(
                url,
                {**(init or {}), "headers": headers}
            )

            return response, current_tokens.access_token

        response, sent_token = await do_request()

        if response.status != 401:
            return response

        # Handle 401 - try to refresh token
        try:
            token_changed = await handle_oauth_401_error(sent_token)
        except Exception:
            token_changed = False

        if not token_changed:
            # Check if token changed underneath us
            current_tokens = get_claudeai_oauth_tokens()
            now = current_tokens.access_token if current_tokens else None
            if not now or now == sent_token:
                return response

        try:
            return (await do_request())[0]
        except Exception:
            return response

    return claudeai_proxy_fetch


# Utilities

def mcp_base_url_analytics(server_ref: ScopedMcpServerConfig) -> Dict[str, Any]:
    """Get analytics-safe server base URL."""
    url = server_ref.get("url") if isinstance(server_ref, dict) else getattr(server_ref, "url", None)
    if url:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return {"mcpServerBaseUrl": f"{parsed.scheme}://{parsed.netloc}"}
    return {}


def handle_remote_auth_failure(
    name: str,
    server_ref: ScopedMcpServerConfig,
    transport_type: str,
) -> NeedsAuthMCPServer:
    """Handle authentication failure for remote transport."""
    set_mcp_auth_cache_entry(name)
    return NeedsAuthMCPServer(
        name=name,
        type="needs-auth",
        config=server_ref,
    )


def get_logging_safe_mcp_base_url(server_ref: ScopedMcpServerConfig) -> Optional[str]:
    """Get base URL for logging (without query params)."""
    url = server_ref.get("url") if isinstance(server_ref, dict) else getattr(server_ref, "url", None)
    if url:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


# Image MIME types for content transformation
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


# Tool Result Types

@dataclass
class MCPToolCallProgress:
    """Progress data from MCP tool call."""
    type: str = "mcp_progress"
    status: str = "progress"
    server_name: Optional[str] = None
    tool_name: Optional[str] = None
    progress: Optional[float] = None
    total: Optional[float] = None
    progress_message: Optional[str] = None
    elapsed_time_ms: Optional[int] = None


# Content Transformation

async def transform_result_content(
    result_content: Dict[str, Any],
    server_name: str,
) -> List[Any]:
    """Transform MCP result content into message blocks."""
    content_type = result_content.get("type")

    if content_type == "text":
        return [{"type": "text", "text": result_content.get("text", "")}]

    elif content_type == "audio":
        return [{"type": "text", "text": f"[Audio from {server_name}] "}]

    elif content_type == "image":
        image_data = result_content
        return [{
            "type": "image",
            "source": {
                "data": image_data.get("data", ""),
                "media_type": image_data.get("mimeType", "image/png"),
                "type": "base64",
            },
        }]

    elif content_type == "resource":
        resource = result_content.get("resource", {})
        uri = resource.get("uri", "")
        prefix = f"[Resource from {server_name} at {uri}] "

        if "text" in resource:
            return [{"type": "text", "text": f"{prefix}{resource.get('text', '')}"}]
        elif "blob" in resource:
            blob = resource.get("blob", "")
            mime_type = resource.get("mimeType", "")
            is_image = mime_type in IMAGE_MIME_TYPES
            if is_image:
                return [{
                    "type": "image",
                    "source": {
                        "data": blob,
                        "media_type": mime_type,
                        "type": "base64",
                    },
                }]
            else:
                return [{"type": "text", "text": f"{prefix}[Binary content]"}]

    elif content_type == "resource_link":
        resource_link = result_content
        name = resource_link.get("name", "")
        uri = resource_link.get("uri", "")
        description = resource_link.get("description", "")
        text = f"[Resource link: {name}] {uri}"
        if description:
            text += f" ({description})"
        return [{"type": "text", "text": text}]

    return []


def infer_compact_schema(value: Any, depth: int = 2) -> str:
    """Generate compact type signature for a value."""
    if value is None:
        return "null"
    if isinstance(value, list):
        if len(value) == 0:
            return "[]"
        return f"[{infer_compact_schema(value[0], depth - 1)}]"
    if isinstance(value, dict):
        if depth <= 0:
            return "{...}"
        entries = list(value.items())[:10]
        props = [f"{k}: {infer_compact_schema(v, depth - 1)}" for k, v in entries]
        suffix = "" if len(value) <= 10 else ", ..."
        return f"{{{', '.join(props)}{suffix}}}"
    return type(value).__name__


async def transform_mcp_result(
    result: Any,
    tool: str,
    name: str,
) -> Dict[str, Any]:
    """Transform MCP tool result into normalized format."""
    if result and isinstance(result, dict):
        if "toolResult" in result:
            return {
                "content": str(result["toolResult"]),
                "type": "toolResult",
            }

        if "structuredContent" in result and result["structuredContent"] is not None:
            import json
            return {
                "content": json.dumps(result["structuredContent"]),
                "type": "structuredContent",
                "schema": infer_compact_schema(result["structuredContent"]),
            }

        if "content" in result and isinstance(result["content"], list):
            transformed_content = []
            for item in result["content"]:
                if isinstance(item, dict):
                    transformed = await transform_result_content(item, name)
                    transformed_content.extend(transformed)
                else:
                    transformed_content.append({"type": "text", "text": str(item)})

            return {
                "content": transformed_content,
                "type": "contentArray",
                "schema": infer_compact_schema(transformed_content),
            }

    error_msg = f'MCP server "{name}" tool "{tool}": unexpected response format'
    logger.error(error_msg)
    raise McpToolCallError(error_msg, error_msg)


def content_contains_images(content: Any) -> bool:
    """Check if content contains image blocks."""
    if not content or not isinstance(content, list):
        return False
    return any(block.get("type") == "image" for block in content)


async def process_mcp_result(
    result: Any,
    tool: str,
    name: str,
) -> Any:
    """Process MCP tool result into final format."""
    from .output_storage import persist_tool_result, is_persist_error
    from .validation import mcp_content_needs_truncation, truncate_mcp_content_if_needed

    try:
        transformed = await transform_mcp_result(result, tool, name)
    except Exception as e:
        logger.error(f"Error transforming MCP result: {e}")
        return [{"type": "text", "text": str(result)}]

    content = transformed.get("content", [])

    # IDE tools don't need large output handling
    if name == "ide":
        return content

    # Check if truncation is needed
    try:
        needs_truncation = await mcp_content_needs_truncation(content)
    except Exception:
        needs_truncation = False

    if not needs_truncation:
        return content

    # If large output files disabled, truncate
    enable_large_output = os.environ.get("ENABLE_MCP_LARGE_OUTPUT_FILES", "true")
    if enable_large_output.lower() in ("false", "0", "no"):
        return await truncate_mcp_content_if_needed(content)

    # If content has images, truncate
    if content_contains_images(content):
        return await truncate_mcp_content_if_needed(content)

    # Persist large output to file
    import json
    timestamp = int(time.time() * 1000)
    persist_id = f"mcp-{name}-{tool}-{timestamp}"
    content_str = content if isinstance(content, str) else json.dumps(content, indent=2)

    persist_result = await persist_tool_result(content_str, persist_id)

    if is_persist_error(persist_result):
        return "Error: result exceeds maximum allowed size. Failed to save output to file."

    return f"Output saved to file. See {persist_result.get('filepath', 'unknown')} ({persist_result.get('originalSize', 0)} bytes)."


# Call MCP Tool

async def call_mcp_tool(
    client: ConnectedMCPServer,
    tool: str,
    args: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
    signal: Optional[Any] = None,
    on_progress: Optional[Callable[[MCPToolCallProgress], None]] = None,
) -> Dict[str, Any]:
    """Call an MCP tool with full error handling and progress support."""
    tool_start_time = time.time()

    try:
        logger.debug(f"Calling MCP tool: {tool}")

        # Set up progress logging every 30 seconds
        def log_progress(elapsed_ms: int) -> None:
            elapsed_sec = elapsed_ms // 1000
            logger.debug(f"Tool '{tool}' still running ({elapsed_sec}s elapsed)")

        # Use client's call_tool method if available
        timeout_ms = get_mcp_tool_timeout_ms()

        # Build call arguments
        call_args = {
            "name": tool,
            "arguments": args,
        }
        if meta:
            call_args["_meta"] = meta

        # Call the tool
        try:
            result = await asyncio.wait_for(
                client.client.call_tool(call_args),
                timeout=timeout_ms / 1000,
            )
        except asyncio.TimeoutError:
            raise McpToolCallError(
                f'MCP server "{client.name}" tool "{tool}" timed out after {timeout_ms // 1000}s',
                "MCP tool timeout",
            )

        # Check for error result
        is_error = result.get("isError", False)
        if is_error:
            error_details = "Unknown error"
            content = result.get("content", [])
            if content and isinstance(content, list):
                first = content[0]
                if isinstance(first, dict) and "text" in first:
                    error_details = first["text"]
            logger.error(f"Tool '{tool}' error: {error_details}")
            raise McpToolCallError(
                error_details,
                "MCP tool returned error",
                mcp_meta=result.get("_meta"),
            )

        elapsed = time.time() - tool_start_time
        duration = f"{int(elapsed * 1000)}ms" if elapsed < 1 else f"{int(elapsed)}s"
        logger.debug(f"Tool '{tool}' completed in {duration}")

        # Process result content
        content = await process_mcp_result(result, tool, client.name)

        return {
            "content": content,
            "_meta": result.get("_meta"),
            "structuredContent": result.get("structuredContent"),
        }

    except McpAuthError:
        raise
    except McpSessionExpiredError:
        raise
    except McpToolCallError:
        raise
    except Exception as e:
        elapsed = time.time() - tool_start_time
        logger.debug(f"Tool '{tool}' failed after {int(elapsed)}s: {e}")
        raise


# Call MCP Tool with URL Elicitation Retry

async def call_mcp_tool_with_url_elicitation_retry(
    client: ConnectedMCPServer,
    client_connection: Any,
    tool: str,
    args: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
    signal: Optional[Any] = None,
    on_progress: Optional[Callable[[MCPToolCallProgress], None]] = None,
) -> Dict[str, Any]:
    """Call MCP tool with URL elicitation retry handling."""
    from .elicitation_handler import run_elicitation_hooks, run_elicitation_result_hooks

    max_retries = 3

    for attempt in range(max_retries + 1):
        try:
            return await call_mcp_tool(
                client=client,
                tool=tool,
                args=args,
                meta=meta,
                signal=signal,
                on_progress=on_progress,
            )
        except McpError as e:
            # Check for URL elicitation required error (-32042)
            if e.code != -32042:
                raise

            error_data = getattr(e, "data", None) or {}
            raw_elicitations = error_data.get("elicitations", [])

            # Filter valid elicitations
            valid_elicitations = []
            for el in raw_elicitations:
                if isinstance(el, dict):
                    if el.get("mode") == "url" and el.get("url") and el.get("elicitationId"):
                        valid_elicitations.append(el)

            if not valid_elicitations:
                logger.debug(f"Tool '{tool}' returned -32042 but no valid elicitations")
                raise

            # Process each elicitation
            for elicitation in valid_elicitations:
                elicitation_id = elicitation.get("elicitationId", "")

                # Run elicitation hooks
                hook_response = await run_elicitation_hooks(
                    client.name,
                    elicitation,
                    signal,
                )
                if hook_response:
                    if hook_response.get("action") != "accept":
                        return {
                            "content": f"URL elicitation was {hook_response.get('action')}ed by a hook."
                        }
                    continue

                # Handle elicitation completion
                user_result = {"action": "cancel"}

                # Run result hooks
                final_result = await run_elicitation_result_hooks(
                    client.name,
                    user_result,
                    signal,
                    "url",
                    elicitation_id,
                )

                if final_result.get("action") != "accept":
                    return {
                        "content": f"URL elicitation was {final_result.get('action')}ed by the user."
                    }

    raise McpError(f"URL elicitation retry limit exceeded for tool '{tool}'", -32042)


# Get MCP Tools, Commands, and Resources

async def get_mcp_tools_commands_and_resources(
    configs: Dict[str, ScopedMcpServerConfig],
    on_connection_attempt: Callable[
        [Dict[str, Any]], None
    ],
) -> None:
    """Connect to MCP servers and fetch their tools, commands, and resources."""
    from .config import get_all_mcp_configs, is_mcp_server_disabled

    # Get all configs if not provided
    if not configs:
        all_configs = await get_all_mcp_configs()
        configs = all_configs.get("servers", {})

    # Partition by disabled and active
    disabled_servers = []
    active_servers = []

    for name, config in configs.items():
        if is_mcp_server_disabled(name):
            disabled_servers.append((name, config))
        else:
            active_servers.append((name, config))

    # Notify about disabled servers
    for name, config in disabled_servers:
        on_connection_attempt({
            "client": {"name": name, "type": "disabled", "config": config},
            "tools": [],
            "commands": [],
        })

    # Process active servers in batches
    local_servers = []
    remote_servers = []

    for name, config in active_servers:
        if is_local_mcp_server(config):
            local_servers.append((name, config))
        else:
            remote_servers.append((name, config))

    async def process_server(item: Tuple[str, ScopedMcpServerConfig]) -> None:
        name, config = item

        try:
            # Skip servers with cached needs-auth
            config_type = config.get("type") if isinstance(config, dict) else getattr(config, "type", None)
            if config_type in ("http", "sse", "claudeai-proxy"):
                if await is_mcp_auth_cached(name):
                    from .auth import has_mcp_discovery_but_no_token
                    if has_mcp_discovery_but_no_token(name, config):
                        on_connection_attempt({
                            "client": {"name": name, "type": "needs-auth", "config": config},
                            "tools": [],
                            "commands": [],
                        })
                        return

            client = await connect_to_server(name, config)

            if client.type != "connected":
                on_connection_attempt({
                    "client": client,
                    "tools": [{"name": "mcp__auth__", "server": name}] if client.type == "needs-auth" else [],
                    "commands": [],
                })
                return

            # Fetch tools, commands, and resources in parallel
            tools, commands, resources = await asyncio.gather(
                fetch_tools_for_client(client),
                fetch_prompts_for_client(client),
                fetch_resources_for_client(client),
            )

            on_connection_attempt({
                "client": client,
                "tools": tools,
                "commands": commands,
                "resources": resources if resources else None,
            })

        except Exception as e:
            logger.error(f"Error fetching MCP resources for '{name}': {e}")
            on_connection_attempt({
                "client": {"name": name, "type": "failed", "config": config},
                "tools": [],
                "commands": [],
            })

    # Process local and remote servers with different batch sizes
    local_batch_size = get_mcp_server_connection_batch_size()
    remote_batch_size = get_remote_mcp_server_connection_batch_size()

    await asyncio.gather(
        process_batched(local_servers, local_batch_size, process_server),
        process_batched(remote_servers, remote_batch_size, process_server),
    )


# Prefetch All MCP Resources

async def prefetch_all_mcp_resources(
    configs: Dict[str, ScopedMcpServerConfig],
) -> Dict[str, Any]:
    """Prefetch all MCP resources (clients, tools, commands)."""
    clients = []
    all_tools = []
    all_commands = []

    pending_count = len(configs)
    completed_count = 0
    results_ready = asyncio.Event()

    async def on_connection(result: Dict[str, Any]) -> None:
        nonlocal completed_count
        completed_count += 1

        clients.append(result.get("client", {}))
        all_tools.extend(result.get("tools", []))
        all_commands.extend(result.get("commands", []))

        if completed_count >= pending_count:
            results_ready.set()

    # Start fetching
    fetch_task = asyncio.create_task(
        get_mcp_tools_commands_and_resources(on_connection, configs)
    )

    # Wait for completion with timeout
    try:
        await asyncio.wait_for(results_ready.wait(), timeout=120)
    except asyncio.TimeoutError:
        logger.warning("Prefetch MCP resources timed out")

    await fetch_task

    return {
        "clients": clients,
        "tools": all_tools,
        "commands": all_commands,
    }


# SDK MCP Client Setup

async def setup_sdk_mcp_clients(
    sdk_configs: Dict[str, Any],
    send_mcp_message: Callable[[str, Dict[str, Any]], Any],
) -> Dict[str, Any]:
    """Set up SDK MCP clients (in-process servers)."""
    clients = []
    tools = []

    for name, config in sdk_configs.items():
        try:
            transport = SdkControlClientTransport(name, send_mcp_message)

            client = MCPClient(
                name=name,
                config=config,
                transport=transport,
            )

            # Connect the client
            await client.send_request("initialize", {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "api-server",
                    "version": "1.0.0",
                },
            })

            # Get capabilities
            capabilities = client.capabilities

            connected_client = ConnectedMCPServer(
                client=client,
                name=name,
                type="connected",
                capabilities=capabilities,
                config=config,
            )

            # Fetch tools
            server_tools = await fetch_tools_for_client(connected_client)

            clients.append(connected_client)
            tools.extend(server_tools)

        except Exception as e:
            logger.error(f"Failed to set up SDK MCP server '{name}': {e}")
            clients.append({
                "name": name,
                "type": "failed",
                "config": config,
            })

    return {
        "clients": clients,
        "tools": tools,
    }


# SdkControlClientTransport (minimal implementation for SDK servers)

class SdkControlClientTransport(MCPTransport):
    """Transport for SDK MCP servers (in-process control channel)."""

    def __init__(
        self,
        server_name: str,
        send_mcp_message: Callable[[str, Dict[str, Any]], Any],
    ):
        self.server_name = server_name
        self.send_mcp_message = send_mcp_message
        self._closed = False
        self._message_queue: Optional[asyncio.Queue] = None
        self.onclose: Optional[Callable[[], None]] = None
        self.onerror: Optional[Callable[[Exception], None]] = None

    @property
    def closed(self) -> bool:
        return self._closed

    async def start(self) -> None:
        self._message_queue = asyncio.Queue()

    async def send(self, message: Dict[str, Any]) -> None:
        if self._closed:
            raise TransportClosedError("Transport is closed")

        try:
            response = await self.send_mcp_message(self.server_name, message)
            if self._message_queue and response:
                await self._message_queue.put(response)
        except Exception as e:
            if self.onerror:
                self.onerror(e)

    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        if not self._message_queue:
            raise TransportClosedError("Message queue not initialized")

        while not self._closed:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0,
                )
                yield message
            except asyncio.TimeoutError:
                continue

    async def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        if self.onclose:
            self.onclose()


# Batch Processing Helper

# Wrap Fetch with Timeout

def wrap_fetch_with_timeout(base_fetch: Callable) -> Callable:
    async def wrapped_fetch(
        url: str,
        init: Optional[Dict[str, Any]] = None,
    ) -> Any:
        method = (init.get("method", "GET") if init else "GET").upper()

        if method == "GET":
            return await base_fetch(url, init)

        headers = dict(init.get("headers", {}) if init else {})
        if "accept" not in headers:
            headers["accept"] = MCP_STREAMABLE_HTTP_ACCEPT

        import threading
        
        timeout_ms = MCP_REQUEST_TIMEOUT_MS
        result_holder = [None, None]
        
        def make_request():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result_holder[0] = loop.run_until_complete(
                    base_fetch(url, {**(init or {}), "headers": headers})
                )
            except Exception as e:
                result_holder[1] = e
            finally:
                loop.close()
        
        thread = threading.Thread(target=make_request)
        thread.daemon = True
        
        import time
        start_time = time.time()
        thread.start()
        
        while thread.is_alive():
            if time.time() - start_time > (timeout_ms / 1000):
                break
            time.sleep(0.01)
        
        thread.join(timeout=1)
        
        if result_holder[1]:
            raise result_holder[1]
        return result_holder[0]

    return wrapped_fetch


# Reconnect MCP Server

async def reconnect_mcp_server(
    name: str,
    config: ScopedMcpServerConfig,
) -> Dict[str, Any]:
    """Reconnect to an MCP server and return fresh client/tools/commands."""
    # Clear keychain cache for fresh credentials
    try:
        from ..utils.secure_storage import clear_keychain_cache
        clear_keychain_cache()
    except ImportError:
        pass

    # Clear server cache
    await clear_server_cache(name, config)

    # Reconnect
    client = await connect_to_server(name, config)

    if client.type != "connected":
        return {
            "client": client,
            "tools": [],
            "commands": [],
        }

    # Fetch resources in parallel
    supports_resources = bool(client.capabilities and client.capabilities.resources)

    tools, commands, resources = await asyncio.gather(
        fetch_tools_for_client(client),
        fetch_prompts_for_client(client),
        fetch_resources_for_client(client) if supports_resources else asyncio.sleep(0).then(lambda: []),
    )

    # Check for resource tools
    if supports_resources:
        has_resource_tools = any(
            t.get("name") in ("list_mcp_resources", "read_mcp_resource")
            for t in tools
        )
        if not has_resource_tools:
            from .resources import ListMcpResourcesTool, ReadMcpResourceTool
            tools = [*tools, ListMcpResourcesTool, ReadMcpResourceTool]

    return {
        "client": client,
        "tools": tools,
        "commands": commands,
        "resources": resources if resources else None,
    }


# Elicitation Handler Integration (stub)

async def run_elicitation_hooks(
    server_name: str,
    elicitation: Dict[str, Any],
    signal: Optional[Any],
) -> Optional[Dict[str, Any]]:
    """Run elicitation hooks. Returns response if hook resolved the elicitation."""
    # Hook integration point - returns None if no hook handles it
    return None


async def run_elicitation_result_hooks(
    server_name: str,
    result: Dict[str, Any],
    signal: Optional[Any],
    elicitation_type: str,
    elicitation_id: str,
) -> Dict[str, Any]:
    """Run elicitation result hooks. Can modify or block the response."""
    return result


# Compare MCP Configs

def are_mcp_configs_equal(a: ScopedMcpServerConfig, b: ScopedMcpServerConfig) -> bool:
    """Compare two MCP server configurations for equality."""
    if a.get("type") != b.get("type"):
        return False

    # Compare by serializing, excluding scope
    import json
    config_a = {k: v for k, v in a.items() if k != "scope"}
    config_b = {k: v for k, v in b.items() if k != "scope"}
    return json.dumps(config_a, sort_keys=True) == json.dumps(config_b, sort_keys=True)


# MCP Tool Input Auto-Classifier

def mcp_tool_input_to_auto_classifier_input(
    input_data: Dict[str, Any],
    tool_name: str,
) -> str:
    """Encode MCP tool input for auto-mode security classifier."""
    keys = list(input_data.keys())
    if keys:
        return " ".join(f"{k}={input_data[k]}" for k in keys)
    return tool_name


# Resource Subscription Lifecycle

async def subscribe_to_resource(
    client: ConnectedMCPServer,
    uri: str,
) -> None:
    """Subscribe to resource changes via resources/subscribe."""
    if not client.capabilities or not client.capabilities.resources:
        return

    supports_subscribe = client.capabilities.resources.get("subscribe", False)
    if not supports_subscribe:
        logger.debug(f"Server {client.name} does not support resource subscription")
        return

    try:
        await client.client.send_notification("resources/subscribe", {
            "uri": uri,
        })
        logger.debug(f"Subscribed to resource: {uri}")
    except Exception as e:
        logger.error(f"Error subscribing to resource '{uri}': {e}")


async def unsubscribe_from_resource(
    client: ConnectedMCPServer,
    uri: str,
) -> None:
    """Unsubscribe from resource changes via resources/unsubscribe."""
    if not client.capabilities or not client.capabilities.resources:
        return

    supports_subscribe = client.capabilities.resources.get("subscribe", False)
    if not supports_subscribe:
        return

    try:
        await client.client.send_notification("resources/unsubscribe", {
            "uri": uri,
        })
        logger.debug(f"Unsubscribed from resource: {uri}")
    except Exception as e:
        logger.error(f"Error unsubscribing from resource '{uri}': {e}")


# Read Resource

async def read_resource(
    client: ConnectedMCPServer,
    uri: str,
) -> Optional[Dict[str, Any]]:
    """Read a resource via resources/read."""
    if not client.capabilities or not client.capabilities.resources:
        return None

    try:
        result = await client.client.send_request("resources/read", {
            "uri": uri,
        })
        return result
    except Exception as e:
        logger.error(f"Error reading resource '{uri}': {e}")
        return None


# Get Prompt (for commands)

async def get_mcp_prompt(
    client: ConnectedMCPServer,
    name: str,
    arguments: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Get prompt content from MCP server."""
    if not client.capabilities or not client.capabilities.prompts:
        return None

    try:
        result = await client.client.send_request("prompts/get", {
            "name": name,
            "arguments": arguments,
        })
        return result
    except Exception as e:
        logger.error(f"Error getting prompt '{name}': {e}")
        return None


# Set Request Handlers

def set_list_roots_handler(
    client: MCPClient,
    handler: Callable[[], Dict[str, Any]],
) -> None:
    """Set handler for ListRoots request from server."""
    client.set_request_handler("roots/list", handler)


def set_elicitation_handler(
    client: MCPClient,
    handler: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> None:
    """Set handler for ElicitRequest from server."""
    client.set_request_handler("elicit", handler)


# Progress Notification Handler

def handle_progress_notification(
    progress_data: Dict[str, Any],
) -> MCPToolCallProgress:
    """Handle progress notification from MCP server."""
    return MCPToolCallProgress(
        type="mcp_progress",
        status=progress_data.get("status", "progress"),
        server_name=progress_data.get("serverName"),
        tool_name=progress_data.get("toolName"),
        progress=progress_data.get("progress"),
        total=progress_data.get("total"),
        progress_message=progress_data.get("message"),
    )


# Logging Helpers

def log_mcp_debug(server_name: str, message: str) -> None:
    """Log debug message for MCP server."""
    logger.debug(f"[MCP/{server_name}] {message}")


def log_mcp_error(server_name: str, message: str) -> None:
    """Log error message for MCP server."""
    logger.error(f"[MCP/{server_name}] {message}")


async def call_ide_rpc(
    tool_name: str,
    args: Dict[str, Any],
    client: ConnectedMCPServer,
) -> Any:
    from ..utils.abort_controller import create_abort_controller
    
    result = await call_mcp_tool(
        client=client,
        tool=tool_name,
        args=args,
        signal=create_abort_controller().signal,
    )
    return result.get("content")


async def reconnect_mcp_server_impl(
    name: str,
    config: ScopedMcpServerConfig,
) -> Dict[str, Any]:
    try:
        try:
            from ..utils.secure_storage import clear_keychain_cache
            clear_keychain_cache()
        except ImportError:
            pass

        await clear_server_cache(name, config)
        
        client = await connect_to_server(name, config)

        if client.type != "connected":
            return {
                "client": client,
                "tools": [],
                "commands": [],
            }

        config_type = config.get("type") if isinstance(config, dict) else getattr(config, "type", None)
        if config_type == "claudeai-proxy":
            try:
                from .claudeai import mark_claudeai_mcp_connected
                mark_claudeai_mcp_connected(name)
            except ImportError:
                pass

        supports_resources = bool(client.capabilities and client.capabilities.resources)

        tools, commands, resources = await asyncio.gather(
            fetch_tools_for_client(client),
            fetch_prompts_for_client(client),
            fetch_resources_for_client(client) if supports_resources else asyncio.sleep(0).then(lambda: []),
        )

        if supports_resources:
            has_resource_tools = any(
                t.get("name") in ("list_mcp_resources", "read_mcp_resource")
                for t in tools
            )
            if not has_resource_tools:
                try:
                    from .resources import ListMcpResourcesTool, ReadMcpResourceTool
                    tools = [*tools, ListMcpResourcesTool, ReadMcpResourceTool]
                except ImportError:
                    pass

        return {
            "client": client,
            "tools": tools,
            "commands": commands,
            "resources": resources if resources else None,
        }
    except Exception as e:
        logger.error(f"Error during reconnection for '{name}': {e}")
        return {
            "client": {"name": name, "type": "failed", "config": config},
            "tools": [],
            "commands": [],
        }


async def persist_blob_to_text_block(
    data: bytes,
    mime_type: Optional[str],
    server_name: str,
    source_description: str,
) -> List[Any]:
    try:
        from ..utils.mcp_output_storage import persist_binary_content, get_binary_blob_saved_message
        
        timestamp = int(time.time() * 1000)
        random_suffix = str(int(time.time() * 1000000))[-6:]
        persist_id = f"mcp-{server_name}-blob-{timestamp}-{random_suffix}"
        
        result = await persist_binary_content(data, mime_type, persist_id)
        
        if "error" in result:
            return [{
                "type": "text",
                "text": f"{source_description}Binary content ({mime_type or 'unknown type'}, {len(data)} bytes) could not be saved to disk: {result['error']}",
            }]
        
        return [{
            "type": "text",
            "text": get_binary_blob_saved_message(
                result.get("filepath", ""),
                mime_type,
                result.get("size", 0),
                source_description,
            ),
        }]
    except Exception as e:
        logger.error(f"Error persisting blob: {e}")
        return [{
            "type": "text",
            "text": f"{source_description}Binary content ({mime_type or 'unknown type'}, {len(data)} bytes) could not be saved to disk",
        }]


async def transform_result_content_extended(
    result_content: Dict[str, Any],
    server_name: str,
) -> List[Any]:
    content_type = result_content.get("type")

    if content_type == "text":
        return [{"type": "text", "text": result_content.get("text", "")}]

    elif content_type == "audio":
        return [{"type": "text", "text": f"[Audio from {server_name}] "}]

    elif content_type == "image":
        image_data = result_content
        return [{
            "type": "image",
            "source": {
                "data": image_data.get("data", ""),
                "media_type": image_data.get("mimeType", "image/png"),
                "type": "base64",
            },
        }]

    elif content_type == "resource":
        resource = result_content.get("resource", {})
        uri = resource.get("uri", "")
        prefix = f"[Resource from {server_name} at {uri}] "

        if "text" in resource:
            return [{"type": "text", "text": f"{prefix}{resource.get('text', '')}"}]
        elif "blob" in resource:
            blob = resource.get("blob", "")
            mime_type = resource.get("mimeType", "")
            is_image = mime_type in IMAGE_MIME_TYPES
            if is_image:
                return [{
                    "type": "image",
                    "source": {
                        "data": blob,
                        "media_type": mime_type,
                        "type": "base64",
                    },
                }]
            else:
                import base64
                try:
                    blob_bytes = base64.b64decode(blob)
                except Exception:
                    blob_bytes = b""
                return await persist_blob_to_text_block(blob_bytes, mime_type, server_name, prefix)

    elif content_type == "resource_link":
        resource_link = result_content
        name_val = resource_link.get("name", "")
        uri = resource_link.get("uri", "")
        description = resource_link.get("description", "")
        text = f"[Resource link: {name_val}] {uri}"
        if description:
            text += f" ({description})"
        return [{"type": "text", "text": text}]

    return []


@dataclass
class MCPToolCallProgressExtended:
    type: str = "mcp_progress"
    status: str = "progress"
    server_name: Optional[str] = None
    tool_name: Optional[str] = None
    progress: Optional[float] = None
    total: Optional[float] = None
    progress_message: Optional[str] = None
    elapsed_time_ms: Optional[int] = None


def handle_progress_notification_extended(
    progress_data: Dict[str, Any],
) -> MCPToolCallProgressExtended:
    return MCPToolCallProgressExtended(
        type="mcp_progress",
        status=progress_data.get("status", "progress"),
        server_name=progress_data.get("serverName"),
        tool_name=progress_data.get("toolName"),
        progress=progress_data.get("progress"),
        total=progress_data.get("total"),
        progress_message=progress_data.get("message"),
        elapsed_time_ms=progress_data.get("elapsedTimeMs"),
    )


async def get_mcp_tools_commands_and_resources_extended(
    on_connection_attempt: Callable[[Dict[str, Any]], None],
    mcp_configs: Optional[Dict[str, ScopedMcpServerConfig]] = None,
) -> None:
    from .config import get_all_mcp_configs, is_mcp_server_disabled

    if not mcp_configs:
        all_configs = await get_all_mcp_configs()
        mcp_configs = all_configs.get("servers", {})

    disabled_servers = []
    active_servers = []

    for name, config in mcp_configs.items():
        if is_mcp_server_disabled(name):
            disabled_servers.append((name, config))
        else:
            active_servers.append((name, config))

    for name, config in disabled_servers:
        on_connection_attempt({
            "client": {"name": name, "type": "disabled", "config": config},
            "tools": [],
            "commands": [],
        })

    local_servers = []
    remote_servers = []

    for name, config in active_servers:
        if is_local_mcp_server(config):
            local_servers.append((name, config))
        else:
            remote_servers.append((name, config))

    resource_tools_added = False

    async def process_server(item: Tuple[str, ScopedMcpServerConfig]) -> None:
        nonlocal resource_tools_added
        name, config = item

        try:
            config_type = config.get("type") if isinstance(config, dict) else getattr(config, "type", None)
            if config_type in ("http", "sse", "claudeai-proxy"):
                if await is_mcp_auth_cached(name):
                    try:
                        from .auth import has_mcp_discovery_but_no_token
                        if has_mcp_discovery_but_no_token(name, config):
                            try:
                                from .auth import create_mcp_auth_tool
                                auth_tool = create_mcp_auth_tool(name, config)
                                on_connection_attempt({
                                    "client": {"name": name, "type": "needs-auth", "config": config},
                                    "tools": [auth_tool] if auth_tool else [],
                                    "commands": [],
                                })
                            except (ImportError, AttributeError):
                                on_connection_attempt({
                                    "client": {"name": name, "type": "needs-auth", "config": config},
                                    "tools": [],
                                    "commands": [],
                                })
                            return
                    except ImportError:
                        pass

            client = await connect_to_server(name, config)

            if client.type != "connected":
                try:
                    from .auth import create_mcp_auth_tool
                    auth_tool = create_mcp_auth_tool(name, config) if client.type == "needs-auth" else None
                    on_connection_attempt({
                        "client": client,
                        "tools": [auth_tool] if auth_tool else [],
                        "commands": [],
                    })
                except (ImportError, AttributeError):
                    on_connection_attempt({
                        "client": client,
                        "tools": [],
                        "commands": [],
                    })
                return

            if config_type == "claudeai-proxy":
                try:
                    from .claudeai import mark_claudeai_mcp_connected
                    mark_claudeai_mcp_connected(name)
                except ImportError:
                    pass

            supports_resources = bool(client.capabilities and client.capabilities.resources)

            tools, commands, resources = await asyncio.gather(
                fetch_tools_for_client(client),
                fetch_prompts_for_client(client),
                fetch_resources_for_client(client) if supports_resources else asyncio.sleep(0).then(lambda: []),
            )

            resource_tools = []
            if supports_resources and not resource_tools_added:
                resource_tools_added = True
                try:
                    from .resources import ListMcpResourcesTool, ReadMcpResourceTool
                    resource_tools = [ListMcpResourcesTool, ReadMcpResourceTool]
                except ImportError:
                    pass

            on_connection_attempt({
                "client": client,
                "tools": [*tools, *resource_tools],
                "commands": commands,
                "resources": resources if resources else None,
            })

        except Exception as e:
            logger.error(f"Error fetching MCP resources for '{name}': {e}")
            on_connection_attempt({
                "client": {"name": name, "type": "failed", "config": config},
                "tools": [],
                "commands": [],
            })

    local_batch_size = get_mcp_server_connection_batch_size()
    remote_batch_size = get_remote_mcp_server_connection_batch_size()

    await asyncio.gather(
        process_batched(local_servers, local_batch_size, process_server),
        process_batched(remote_servers, remote_batch_size, process_server),
    )


async def prefetch_all_mcp_resources_extended(
    mcp_configs: Dict[str, ScopedMcpServerConfig],
) -> Dict[str, Any]:
    clients = []
    all_tools = []
    all_commands = []

    pending_count = len(mcp_configs)
    completed_count = 0
    results_ready = asyncio.Event()

    async def on_connection(result: Dict[str, Any]) -> None:
        nonlocal completed_count
        completed_count += 1

        clients.append(result.get("client", {}))
        all_tools.extend(result.get("tools", []))
        all_commands.extend(result.get("commands", []))

        if completed_count >= pending_count:
            results_ready.set()

    fetch_task = asyncio.create_task(
        get_mcp_tools_commands_and_resources_extended(on_connection, mcp_configs)
    )

    try:
        await asyncio.wait_for(results_ready.wait(), timeout=120)
    except asyncio.TimeoutError:
        logger.warning("Prefetch MCP resources timed out")

    await fetch_task

    return {
        "clients": clients,
        "tools": all_tools,
        "commands": all_commands,
    }


async def setup_sdk_mcp_clients_extended(
    sdk_configs: Dict[str, Any],
    send_mcp_message: Callable[[str, Dict[str, Any]], Any],
) -> Dict[str, Any]:
    clients = []
    tools = []

    for name, config in sdk_configs.items():
        try:
            transport = SdkControlClientTransport(name, send_mcp_message)

            client = MCPClient(
                name=name,
                config=config,
                transport=transport,
            )

            await client.send_request("initialize", {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "api-server",
                    "version": "1.0.0",
                },
            })

            capabilities = client.capabilities

            connected_client = ConnectedMCPServer(
                client=client,
                name=name,
                type="connected",
                capabilities=capabilities,
                config=config,
            )

            server_tools = await fetch_tools_for_client(connected_client)

            clients.append(connected_client)
            tools.extend(server_tools)

        except Exception as e:
            logger.error(f"Failed to set up SDK MCP server '{name}': {e}")
            clients.append({
                "name": name,
                "type": "failed",
                "config": config,
            })

    return {
        "clients": clients,
        "tools": tools,
    }


def get_session_ingress_auth_token() -> Optional[str]:
    try:
        from ..utils.session_ingress_auth import get_session_ingress_auth_token as get_token
        return get_token()
    except ImportError:
        return None


def mcp_base_url_analytics_extended(server_ref: ScopedMcpServerConfig) -> Dict[str, Any]:
    url = server_ref.get("url") if isinstance(server_ref, dict) else getattr(server_ref, "url", None)
    if url:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return {"mcpServerBaseUrl": f"{parsed.scheme}://{parsed.netloc}"}
    return {}


def extract_tool_use_id(message: Any) -> Optional[str]:
    """Extract tool use ID from message if it's a tool_use message."""
    try:
        if message and hasattr(message, "message"):
            content = message.message.content if hasattr(message.message, "content") else None
            if content and isinstance(content, list) and len(content) > 0:
                first = content[0]
                if hasattr(first, "type") and first.type == "tool_use":
                    return getattr(first, "id", None)
        return None
    except Exception:
        return None


TERMINAL_CONNECTION_ERRORS = [
    "ECONNRESET",
    "ETIMEDOUT",
    "EPIPE",
    "EHOSTUNREACH",
    "ECONNREFUSED",
    "Body Timeout Error",
    "terminated",
    "SSE stream disconnected",
    "Failed to reconnect SSE stream",
    "Maximum reconnection attempts",
]
