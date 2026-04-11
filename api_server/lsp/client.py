import asyncio
import json
from typing import Any, Callable

from .types import LspServerState


LSP_ERROR_CONTENT_MODIFIED = -32801
MAX_RETRIES_FOR_TRANSIENT_ERRORS = 3
RETRY_BASE_DELAY_MS = 500


class LSPClient:
    def __init__(
        self,
        server_name: str,
        command: str,
        cwd: str | None = None,
        on_crash: Callable[[Exception], None] | None = None,
    ):
        self.server_name = server_name
        self.command = command
        self.cwd = cwd
        self.on_crash = on_crash
        
        self.process: asyncio.subprocess.Process | None = None
        self.request_id = 0
        self.pending_requests: dict[int, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None
        self._state: LspServerState = LspServerState.STOPPED
        self._is_initialized = False
        self._start_failed = False
        self._start_error: Exception | None = None
        self._is_stopping = False
        
        self._notification_handlers: dict[str, Callable[[Any], None]] = {}
        self._request_handlers: dict[str, Callable[[Any], Any]] = {}

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    async def start(
        self,
        command: str,
        args: list[str],
        options: dict[str, Any] | None = None,
    ) -> bool:
        try:
            env = None
            cwd = self.cwd
            if options:
                env = options.get("env")
                cwd = options.get("cwd") or self.cwd

            self.process = await asyncio.create_subprocess_exec(
                command,
                *args,
                cwd=cwd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            
            self._state = LspServerState.STARTING
            self._reader_task = asyncio.create_task(self._read_messages())
            
            return True
        except Exception as e:
            self._start_failed = True
            self._start_error = e
            self._state = LspServerState.ERROR
            return False

    async def initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.process:
            raise Exception("LSP client not started")
        
        if self._start_failed:
            raise self._start_error or Exception(f"LSP server {self.server_name} failed to start")

        try:
            result = await self.send_request("initialize", params)
            await self.send_notification("initialized", {})
            self._is_initialized = True
            self._state = LspServerState.RUNNING
            return result
        except Exception as e:
            self._state = LspServerState.ERROR
            raise e

    async def send_request(self, method: str, params: Any) -> Any:
        if not self.process:
            raise Exception("LSP client not started")
        
        if self._start_failed:
            raise self._start_error or Exception(f"LSP server {self.server_name} failed to start")

        if not self._is_initialized:
            raise Exception("LSP server not initialized")

        self.request_id += 1
        req_id = self.request_id
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[req_id] = future

        msg = json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        })
        self.process.stdin.write((msg + "\n").encode())
        await self.process.stdin.drain()

        return await future

    async def send_notification(self, method: str, params: Any) -> None:
        if not self.process:
            raise Exception("LSP client not started")
        
        if self._start_failed:
            raise self._start_error or Exception(f"LSP server {self.server_name} failed to start")

        try:
            msg = json.dumps({
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            })
            self.process.stdin.write((msg + "\n").encode())
            await self.process.stdin.drain()
        except Exception:
            pass

    def on_notification(self, method: str, handler: Callable[[Any], None]) -> None:
        if not self._reader_task:
            self._notification_handlers[method] = handler
        else:
            pass

    def on_request(
        self,
        method: str,
        handler: Callable[[Any], Any],
    ) -> None:
        self._request_handlers[method] = handler

    async def close(self) -> None:
        self._is_stopping = True
        
        try:
            if self.process:
                try:
                    await self.send_request("shutdown", {})
                    await self.send_notification("exit", {})
                except Exception:
                    pass
                
                self.process.terminate()
                await self.process.wait()
        except Exception:
            pass
        finally:
            if self._reader_task:
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass
            
            self.process = None
            self._state = LspServerState.STOPPED
            self._is_initialized = False
            self._is_stopping = False

    async def _read_messages(self) -> None:
        if not self.process or not self.process.stdout:
            return
        
        reader = self.process.stdout
        buffer = b""
        
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                
                buffer += chunk
                
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode())
                        await self._handle_message(msg)
                    except Exception:
                        continue
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _handle_message(self, msg: dict) -> None:
        method = msg.get("method")
        msg_id = msg.get("id")
        
        if method and msg_id:
            handler = self._request_handlers.get(method)
            if handler:
                result = handler(msg.get("params"))
                if asyncio.iscoroutine(result):
                    result = await result
                
                response = json.dumps({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result,
                })
                if self.process and self.process.stdin:
                    self.process.stdin.write((response + "\n").encode())
                    await self.process.stdin.drain()
            return
        
        if method:
            handler = self._notification_handlers.get(method)
            if handler:
                handler(msg.get("params"))
            return
        
        if msg_id and msg_id in self.pending_requests:
            future = self.pending_requests.pop(msg_id)
            if "error" in msg:
                future.set_result({"error": msg["error"]})
            else:
                future.set_result(msg.get("result"))

    async def stop(self) -> None:
        await self.close()