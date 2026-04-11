"""
In-process linked transport pair for running an MCP server and client
in the same process without spawning a subprocess.
"""

import asyncio
from typing import Any, Callable, Dict, Optional


class InProcessTransport:
    """
    In-process linked transport for MCP communication.

    Messages sent on one side are delivered to `onmessage` on the other.
    `close()` on either side calls `onclose` on both.
    """

    def __init__(self):
        self._peer: Optional["InProcessTransport"] = None
        self._closed = False
        self.onclose: Optional[Callable[[], None]] = None
        self.onerror: Optional[Callable[[Exception], None]] = None
        self.onmessage: Optional[Callable[[Dict[str, Any]], None]] = None

    def _set_peer(self, peer: "InProcessTransport") -> None:
        self._peer = peer

    async def start(self) -> None:
        pass

    async def send(self, message: Dict[str, Any]) -> None:
        if self._closed:
            raise Error("Transport is closed")
        if not self._peer:
            raise Error("No peer transport connected")

        asyncio.get_event_loop().call_soon(
            lambda: self._peer.onmessage and self._peer.onmessage(message)
        )

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.onclose()
        if self._peer and not self._peer._closed:
            self._peer._closed = True
            self._peer.onclose()


def create_linked_transport_pair() -> tuple:
    """
    Creates a pair of linked transports for in-process MCP communication.
    Messages sent on one transport are delivered to the other's `onmessage`.

    Returns:
        Tuple of (client_transport, server_transport)
    """
    a = InProcessTransport()
    b = InProcessTransport()
    a._set_peer(b)
    b._set_peer(a)
    return a, b


class Error(Exception):
    """Transport error."""
    pass
