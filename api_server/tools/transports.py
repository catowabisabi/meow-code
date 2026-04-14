"""CLI transports - bridging gap with TypeScript cli/transports/"""
import asyncio
import logging
import json
from typing import Callable, Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass
from enum import Enum

try:
    import sseclient
    HAS_SSECLIENT = True
except ImportError:
    HAS_SSECLIENT = False
    sseclient = None

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    websockets = None


logger = logging.getLogger(__name__)


class TransportState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class TransportMessage:
    type: str
    data: Any
    metadata: Optional[Dict[str, Any]] = None


class BaseTransport:
    def __init__(self):
        self.state = TransportState.DISCONNECTED
        self._message_handlers: list[Callable] = []
        self._error_handlers: list[Callable] = []
    
    async def connect(self) -> None:
        raise NotImplementedError
    
    async def disconnect(self) -> None:
        raise NotImplementedError
    
    async def send(self, message: TransportMessage) -> None:
        raise NotImplementedError
    
    def on_message(self, handler: Callable) -> None:
        self._message_handlers.append(handler)
    
    def on_error(self, handler: Callable) -> None:
        self._error_handlers.append(handler)
    
    def _notify_message(self, message: TransportMessage) -> None:
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")
    
    def _notify_error(self, error: Exception) -> None:
        for handler in self._error_handlers:
            try:
                handler(error)
            except Exception as e:
                logger.error(f"Error handler error: {e}")


class SSETransport(BaseTransport):
    """
    Server-Sent Events transport.
    
    TypeScript equivalent: SSETransport.ts
    Python gap: No Python SSE transport implementation.
    """
    
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        super().__init__()
        self.url = url
        self.headers = headers or {}
        self._session: Optional[Any] = None
        self._client: Optional[sseclient.SSEClient] = None
    
    async def connect(self) -> None:
        self.state = TransportState.CONNECTING
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                self._session = session
                
                async with session.get(self.url, headers=self.headers) as response:
                    if response.status != 200:
                        raise Exception(f"SSE connection failed: {response.status}")
                    
                    self.state = TransportState.CONNECTED
                    self._client = sseclient.SSEClient(response)
                    
                    async for event in self._client:
                        if event.event == "message":
                            try:
                                data = json.loads(event.data)
                                message = TransportMessage(
                                    type="sse",
                                    data=data,
                                    metadata={"event": event.event}
                                )
                                self._notify_message(message)
                            except json.JSONDecodeError:
                                message = TransportMessage(
                                    type="sse",
                                    data=event.data,
                                    metadata={"event": event.event}
                                )
                                self._notify_message(message)
                        
                        elif event.event == "error":
                            self._notify_error(Exception(event.data))
                        
                        elif event.event == "close":
                            break
        
        except Exception as e:
            self.state = TransportState.ERROR
            self._notify_error(e)
    
    async def send(self, message: TransportMessage) -> None:
        if self.state != TransportState.CONNECTED:
            raise Exception("Not connected")
        
        if self._session:
            async with self._session.post(
                self.url.replace("/sse", "/events"),
                json=message.data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status not in (200, 201):
                    raise Exception(f"Failed to send: {response.status}")
    
    async def disconnect(self) -> None:
        self.state = TransportState.DISCONNECTED
        if self._session:
            await self._session.close()
            self._session = None


class WebSocketTransport(BaseTransport):
    """
    WebSocket transport.
    
    TypeScript equivalent: WebSocketTransport.ts
    Python gap: No Python WebSocket transport implementation.
    """
    
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        ping_interval: int = 30
    ):
        super().__init__()
        self.url = url
        self.headers = headers or {}
        self.ping_interval = ping_interval
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> None:
        self.state = TransportState.CONNECTING
        
        try:
            self._ws = await websockets.connect(
                self.url,
                extra_headers=self.headers
            )
            
            self.state = TransportState.CONNECTED
            
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._ping_task = asyncio.create_task(self._ping_loop())
        
        except Exception as e:
            self.state = TransportState.ERROR
            self._notify_error(e)
    
    async def _receive_loop(self) -> None:
        if not self._ws:
            return
        
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8")
                
                try:
                    data = json.loads(message)
                    transport_msg = TransportMessage(type="ws", data=data)
                    self._notify_message(transport_msg)
                except json.JSONDecodeError:
                    transport_msg = TransportMessage(type="ws", data=message)
                    self._notify_message(transport_msg)
        
        except websockets.ConnectionClosed:
            self.state = TransportState.DISCONNECTED
        except Exception as e:
            self.state = TransportState.ERROR
            self._notify_error(e)
    
    async def _ping_loop(self) -> None:
        while self.state == TransportState.CONNECTED:
            await asyncio.sleep(self.ping_interval)
            if self._ws and self.state == TransportState.CONNECTED:
                try:
                    await self._ws.ping()
                except Exception:
                    break
    
    async def send(self, message: TransportMessage) -> None:
        if not self._ws or self.state != TransportState.CONNECTED:
            raise Exception("Not connected")
        
        data = json.dumps(message.data)
        await self._ws.send(data)
    
    async def disconnect(self) -> None:
        self.state = TransportState.DISCONNECTED
        
        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None
        
        if self._receive_task:
            self._receive_task.cancel()
            self._receive_task = None
        
        if self._ws:
            await self._ws.close()
            self._ws = None


class HybridTransport(BaseTransport):
    """
    Hybrid transport combining SSE for server-to-client and WebSocket for client-to-server.
    
    TypeScript equivalent: HybridTransport.ts
    Python gap: No Python hybrid transport implementation.
    """
    
    def __init__(
        self,
        sse_url: str,
        ws_url: str,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__()
        self.sse_transport = SSETransport(sse_url, headers)
        self.ws_transport = WebSocketTransport(ws_url, headers)
        self._forward_to_ws = True
    
    async def connect(self) -> None:
        self.state = TransportState.CONNECTING
        
        self.sse_transport.on_message(self._handle_sse_message)
        self.ws_transport.on_message(self._handle_ws_message)
        
        await asyncio.gather(
            self.sse_transport.connect(),
            self.ws_transport.connect()
        )
        
        self.state = TransportState.CONNECTED
    
    def _handle_sse_message(self, message: TransportMessage) -> None:
        self._notify_message(message)
    
    def _handle_ws_message(self, message: TransportMessage) -> None:
        if self._forward_to_ws:
            self._notify_message(message)
    
    async def send(self, message: TransportMessage) -> None:
        if self.state != TransportState.CONNECTED:
            raise Exception("Not connected")
        
        await self.ws_transport.send(message)
    
    async def disconnect(self) -> None:
        self.state = TransportState.DISCONNECTED
        await self.sse_transport.disconnect()
        await self.ws_transport.disconnect()
