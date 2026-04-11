"""
SDK MCP Transport Bridge

This module implements a transport bridge that allows MCP servers running in the SDK process
to communicate with the Claude Code CLI process through control messages.
"""

from typing import Any, Callable, Dict, Optional


class SdkControlClientTransport:
    """
    CLI-side transport for SDK MCP servers.

    This transport is used in the CLI process to bridge communication between:
    - The CLI's MCP Client (which wants to call tools on SDK MCP servers)
    - The SDK process (where the actual MCP server runs)

    It converts MCP protocol messages into control requests that can be sent
    through stdout/stdin to the SDK process.
    """

    def __init__(
        self,
        server_name: str,
        send_mcp_message: Callable[[str, Dict[str, Any]], Any],
    ):
        self._server_name = server_name
        self._send_mcp_message = send_mcp_message
        self._is_closed = False
        self.onclose: Optional[Callable[[], None]] = None
        self.onerror: Optional[Callable[[Exception], None]] = None
        self.onmessage: Optional[Callable[[Dict[str, Any]], None]] = None

    async def start(self) -> None:
        pass

    async def send(self, message: Dict[str, Any]) -> None:
        if self._is_closed:
            raise Error("Transport is closed")

        response = await self._send_mcp_message(self._server_name, message)

        if self.onmessage:
            self.onmessage(response)

    async def close(self) -> None:
        if self._is_closed:
            return
        self._is_closed = True
        if self.onclose:
            self.onclose()


class SdkControlServerTransport:
    """
    SDK-side transport for SDK MCP servers.

    This transport is used in the SDK process to bridge communication between:
    - Control requests coming from the CLI (via stdin)
    - The actual MCP server running in the SDK process

    It acts as a simple pass-through that forwards messages to the MCP server
    and sends responses back via a callback.
    """

    def __init__(self, send_mcp_message: Callable[[Dict[str, Any]], None]):
        self._send_mcp_message = send_mcp_message
        self._is_closed = False
        self.onclose: Optional[Callable[[], None]] = None
        self.onerror: Optional[Callable[[Exception], None]] = None
        self.onmessage: Optional[Callable[[Dict[str, Any]], None]] = None

    async def start(self) -> None:
        pass

    async def send(self, message: Dict[str, Any]) -> None:
        if self._is_closed:
            raise Error("Transport is closed")

        self._send_mcp_message(message)

    async def close(self) -> None:
        if self._is_closed:
            return
        self._is_closed = True
        if self.onclose:
            self.onclose()


class Error(Exception):
    """Transport error."""
    pass
