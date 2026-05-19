import asyncio
import json
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

class LSPTransport(Enum):
    STDIO = "stdio"
    TCP = "tcp"
    WEBSOCKET = "websocket"

@dataclass
class LSPMessage:
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class LSPClient:
    def __init__(
        self,
        command: str,
        args: Optional[list[str]] = None,
        transport: LSPTransport = LSPTransport.STDIO,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        self.command = command
        self.args = args or []
        self.transport = transport
        self.host = host
        self.port = port
        self.process: Optional[asyncio.subprocess.Process] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.message_id = 0
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.notification_handlers: Dict[str, Callable] = {}
        self._receive_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self.transport == LSPTransport.STDIO:
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self.reader = self.process.stdout
            self.writer = self.process.stdin
        elif self.transport == LSPTransport.TCP:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def stop(self) -> None:
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self.process:
            self.process.terminate()
            await self.process.wait()
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def send_request(self, method: str, params: Optional[dict] = None) -> Any:
        self.message_id += 1
        msg_id = str(self.message_id)
        message = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method,
            "params": params or {},
        }
        await self._send_message(message)
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[msg_id] = future
        try:
            return await future
        finally:
            self.pending_requests.pop(msg_id, None)

    async def send_notification(self, method: str, params: Optional[dict] = None) -> None:
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        await self._send_message(message)

    def on_notification(self, method: str, handler: Callable) -> None:
        self.notification_handlers[method] = handler

    async def _send_message(self, message: dict) -> None:
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        if self.writer:
            self.writer.write((header + content).encode())
            await self.writer.drain()

    async def _receive_loop(self) -> None:
        while True:
            try:
                header_line = await self.reader.readline() if self.reader else b""
                if not header_line:
                    break
                header = header_line.decode().strip()
                if not header.startswith("Content-Length:"):
                    continue
                content_length = int(header.split(":")[1].strip())
                await self.reader.read(2)
                content = await self.reader.read(content_length) if self.reader else b""
                message = json.loads(content.decode())
                await self._handle_message(message)
            except Exception:
                break

    async def _handle_message(self, message: dict) -> None:
        if "id" in message:
            msg_id = message["id"]
            if msg_id in self.pending_requests:
                if "result" in message:
                    self.pending_requests[msg_id].set_result(message["result"])
                elif "error" in message:
                    self.pending_requests[msg_id].set_exception(Exception(message["error"]))
        elif "method" in message:
            method = message["method"]
            if method in self.notification_handlers:
                handler = self.notification_handlers[method]
                if asyncio.iscoroutinefunction(handler):
                    await handler(message.get("params"))
                else:
                    handler(message.get("params"))

class LSPServerManager:
    def __init__(self):
        self.servers: Dict[str, LSPClient] = {}

    async def start_server(
        self,
        language: str,
        command: str,
        args: Optional[list[str]] = None,
        root_uri: Optional[str] = None,
    ) -> LSPClient:
        client = LSPClient(command, args)
        await client.start()
        
        await client.send_request("initialize", {
            "processId": None,
            "rootUri": root_uri,
            "capabilities": {},
        })
        await client.send_notification("initialized", {})
        
        self.servers[language] = client
        return client

    async def stop_server(self, language: str) -> None:
        if language in self.servers:
            await self.servers[language].stop()
            del self.servers[language]

    def get_server(self, language: str) -> Optional[LSPClient]:
        return self.servers.get(language)