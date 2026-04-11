"""LSP Client - JSON-RPC protocol over stdio."""

import asyncio
import json
import os
import signal
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


@dataclass
class ServerCapabilities:
    pass


@dataclass
class InitializeResult:
    capabilities: ServerCapabilities


LSP_ERROR_CONTENT_MODIFIED = -32801


@dataclass
class PendingHandler:
    method: str
    handler: Callable[[Any], None]


@dataclass
class PendingRequestHandler:
    method: str
    handler: Callable[[Any], Any]


class LSPClient:
    def __init__(
        self,
        server_name: str,
        on_crash: Optional[Callable[[Exception], None]] = None,
    ):
        self._server_name = server_name
        self._on_crash = on_crash
        self._process: Optional[asyncio.subprocess.Process] = None
        self._capabilities: Optional[ServerCapabilities] = None
        self._is_initialized = False
        self._start_failed = False
        self._start_error: Optional[Exception] = None
        self._is_stopping = False
        self._pending_handlers: List[PendingHandler] = []
        self._pending_request_handlers: List[PendingRequestHandler] = []
        self._request_handlers: Dict[str, Callable[[Any], Any]] = {}
        self._notification_handlers: Dict[str, Callable[[Any], None]] = {}
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None

    @property
    def capabilities(self) -> Optional[ServerCapabilities]:
        return self._capabilities

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    def _check_start_failed(self) -> None:
        if self._start_failed:
            raise self._start_error or Exception(
                f"LSP server {self._server_name} failed to start"
            )

    async def start(
        self,
        command: str,
        args: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        env = os.environ.copy()
        if options and options.get("env"):
            env.update(options["env"])
        cwd = options.get("cwd") if options else None

        try:
            self._process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
                close_fds=False,
            )

            if self._process.stdout is None or self._process.stdin is None:
                raise Exception("LSP server process stdio not available")

            self._reader_task = asyncio.create_task(self._read_messages())

            asyncio.create_task(self._read_stderr())

            self._process.add_signal_handler(signal.SIGTERM, lambda: None)

            self._is_stopping = False

            for handler in self._pending_handlers:
                self._notification_handlers[handler.method] = handler.handler
            self._pending_handlers.clear()

            for handler in self._pending_request_handlers:
                self._request_handlers[handler.method] = handler.handler
            self._pending_request_handlers.clear()

        except Exception as error:
            self._start_failed = True
            self._start_error = error if isinstance(error, Exception) else Exception(str(error))
            raise

    async def _read_stderr(self) -> None:
        if self._process and self._process.stderr:
            try:
                while True:
                    line = await self._process.stderr.readline()
                    if not line:
                        break
                    data = line.decode().strip()
                    if data:
                        pass
            except Exception:
                pass

    async def _read_messages(self) -> None:
        if self._process is None or self._process.stdout is None:
            return

        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break

                try:
                    message = json.loads(line.decode())
                except json.JSONDecodeError:
                    continue

                if isinstance(message, dict):
                    if message.get("id"):
                        msg_id = message["id"]
                        if msg_id in self._response_futures:
                            future = self._response_futures.pop(msg_id)
                            if "error" in message:
                                future.set_exception(Exception(message["error"].get("message", "Unknown error")))
                            else:
                                future.set_result(message.get("result"))
                        elif msg_id in self._request_handlers:
                            handler = self._request_handlers[msg_id]
                            result = handler(message.get("params"))
                            await self._send_raw({"jsonrpc": "2.0", "id": msg_id, "result": result})
                    elif message.get("method"):
                        method = message["method"]
                        params = message.get("params")
                        if method in self._notification_handlers:
                            self._notification_handlers[method](params)
                        elif method in self._request_handlers:
                            handler = self._request_handlers[method]
                            result = handler(params)
                            msg_id = message.get("id")
                            if msg_id is not None:
                                await self._send_raw({"jsonrpc": "2.0", "id": msg_id, "result": result})
        except asyncio.CancelledError:
            pass
        except Exception as error:
            if not self._is_stopping:
                self._start_failed = True
                self._start_error = error if isinstance(error, Exception) else Exception(str(error))
                if self._on_crash:
                    self._on_crash(error)

    async def _send_raw(self, message: Dict[str, Any]) -> None:
        if self._process and self._process.stdin:
            content = json.dumps(message)
            header = f"Content-Length: {len(content)}\r\n\r\n"
            self._process.stdin.write((header + content).encode())
            await self._process.stdin.drain()

    async def initialize(self, params: Dict[str, Any]) -> InitializeResult:
        if not self._process:
            raise Exception("LSP client not started")

        self._check_start_failed()

        await self.send_request("initialize", params)

        self._is_initialized = True

        await self.send_notification("initialized", {})

        return InitializeResult(
            capabilities=self._capabilities or ServerCapabilities()
        )

    async def send_request(self, method: str, params: Any) -> Any:
        if not self._process:
            raise Exception("LSP client not started")

        self._check_start_failed()

        if not self._is_initialized:
            raise Exception("LSP server not initialized")

        msg_id = str(uuid4())
        message = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}

        future = asyncio.get_event_loop().create_future()
        self._response_futures[msg_id] = future

        try:
            await self._send_raw(message)
            return await future
        except Exception:
            self._response_futures.pop(msg_id, None)
            raise

    async def send_notification(self, method: str, params: Any) -> None:
        if not self._process:
            raise Exception("LSP client not started")

        self._check_start_failed()

        message = {"jsonrpc": "2.0", "method": method, "params": params}
        await self._send_raw(message)

    def on_notification(self, method: str, handler: Callable[[Any], None]) -> None:
        if not self._process:
            self._pending_handlers.append(PendingHandler(method=method, handler=handler))
            return

        self._check_start_failed()
        self._notification_handlers[method] = handler

    def on_request(
        self, method: str, handler: Callable[[Any], Any]
    ) -> None:
        if not self._process:
            self._pending_request_handlers.append(
                PendingRequestHandler(method=method, handler=handler)
            )
            return

        self._check_start_failed()
        self._request_handlers[method] = handler

    async def stop(self) -> None:
        self._is_stopping = True

        try:
            if self._process:
                try:
                    await self.send_request("shutdown", {})
                    await self.send_notification("exit", {})
                except Exception:
                    pass

                if self._reader_task:
                    self._reader_task.cancel()
                    try:
                        await self._reader_task
                    except asyncio.CancelledError:
                        pass

                try:
                    self._process.terminate()
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self._process.kill()
                    await self._process.wait()
                except Exception:
                    pass

        finally:
            if self._process:
                self._process = None

            self._response_futures.clear()
            self._is_initialized = False
            self._capabilities = None
            self._is_stopping = False


def create_lsp_client(
    server_name: str,
    on_crash: Optional[Callable[[Exception], None]] = None,
) -> LSPClient:
    return LSPClient(server_name=server_name, on_crash=on_crash)
