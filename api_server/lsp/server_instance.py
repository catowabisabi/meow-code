import asyncio
import os
from typing import Any, Callable

from .client import LSPClient
from .types import LspServerState, ScopedLspServerConfig


MAX_RETRIES_FOR_TRANSIENT_ERRORS = 3
RETRY_BASE_DELAY_MS = 500


class LSPServerInstance:
    def __init__(self, name: str, config: ScopedLspServerConfig):
        self.name = name
        self.config = config
        
        self._client = LSPClient(name, config.command)
        self._state: LspServerState = LspServerState.STOPPED
        self._start_time: Any = None
        self._last_error: Exception | None = None
        self._restart_count = 0
        self._crash_recovery_count = 0
        
        self._notification_handlers: dict[str, Callable[[Any], None]] = {}
        self._request_handlers: dict[str, Callable[[Any], Any]] = {}

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def start_time(self) -> Any:
        return self._start_time

    @property
    def last_error(self) -> Exception | None:
        return self._last_error

    @property
    def restart_count(self) -> int:
        return self._restart_count

    @property
    def is_healthy(self) -> bool:
        return self._state == LspServerState.RUNNING and self._client.is_initialized

    async def start(self) -> None:
        if self._state == LspServerState.RUNNING or self._state == LspServerState.STARTING:
            return

        max_restarts = self.config.max_restarts or 3
        if self._state == LspServerState.ERROR and self._crash_recovery_count > max_restarts:
            error = Exception(f"LSP server '{self.name}' exceeded max crash recovery attempts ({max_restarts})")
            self._last_error = error
            raise error

        self._state = LspServerState.STARTING

        try:
            await self._client.start(
                self.config.command,
                self.config.args or [],
                options={"env": self.config.env, "cwd": self.config.workspace_folder},
            )

            workspace_folder = self.config.workspace_folder or os.getcwd()
            
            init_params: dict[str, Any] = {
                "processId": os.getpid(),
                "initializationOptions": self.config.initialization_options or {},
                "workspaceFolders": [{"uri": workspace_folder, "name": os.path.basename(workspace_folder)}],
                "rootPath": workspace_folder,
                "rootUri": workspace_folder,
                "capabilities": {
                    "workspace": {"configuration": False, "workspaceFolders": False},
                    "textDocument": {
                        "synchronization": {"dynamicRegistration": False, "willSave": False, "willSaveWaitUntil": False, "didSave": True},
                        "publishDiagnostics": {"relatedInformation": True, "tagSupport": {"valueSet": [1, 2]}, "versionSupport": False, "codeDescriptionSupport": True, "dataSupport": False},
                        "hover": {"dynamicRegistration": False, "contentFormat": ["markdown", "plaintext"]},
                        "definition": {"dynamicRegistration": False, "linkSupport": True},
                        "references": {"dynamicRegistration": False},
                        "documentSymbol": {"dynamicRegistration": False, "hierarchicalDocumentSymbolSupport": True},
                        "callHierarchy": {"dynamicRegistration": False},
                    },
                    "general": {"positionEncodings": ["utf-16"]},
                },
            }

            init_promise = self._client.initialize(init_params)
            if self.config.startup_timeout:
                await with_timeout(init_promise, self.config.startup_timeout, f"LSP server '{self.name}' timed out during initialization")
            else:
                await init_promise

            self._state = LspServerState.RUNNING
            self._start_time = asyncio.get_event_loop().time()
            self._crash_recovery_count = 0

        except Exception as e:
            try:
                await self._client.close()
            except Exception:
                pass
            self._state = LspServerState.ERROR
            self._last_error = e
            raise e

    async def stop(self) -> None:
        if self._state == LspServerState.STOPPED or self._state == LspServerState.STOPPING:
            return

        try:
            self._state = LspServerState.STOPPING
            await self._client.close()
            self._state = LspServerState.STOPPED
        except Exception as e:
            self._state = LspServerState.ERROR
            self._last_error = e
            raise e

    async def restart(self) -> None:
        try:
            await self.stop()
        except Exception as e:
            raise Exception(f"Failed to stop LSP server '{self.name}' during restart: {e}")

        self._restart_count += 1

        max_restarts = self.config.max_restarts or 3
        if self._restart_count > max_restarts:
            raise Exception(f"Max restart attempts ({max_restarts}) exceeded for server '{self.name}'")

        try:
            await self.start()
        except Exception as e:
            raise Exception(f"Failed to start LSP server '{self.name}' during restart (attempt {self._restart_count}/{max_restarts}): {e}")

    async def send_request(self, method: str, params: Any) -> Any:
        if not self.is_healthy:
            raise Exception(f"Cannot send request to LSP server '{self.name}': server is {self._state}")

        last_error = None
        for attempt in range(MAX_RETRIES_FOR_TRANSIENT_ERRORS + 1):
            try:
                return await self._client.send_request(method, params)
            except Exception as e:
                last_error = e
                error_code = getattr(e, "code", None)
                is_content_modified = error_code == -32801

                if is_content_modified and attempt < MAX_RETRIES_FOR_TRANSIENT_ERRORS:
                    delay = RETRY_BASE_DELAY_MS * (2 ** attempt)
                    await asyncio.sleep(delay / 1000)
                    continue
                break

        raise Exception(f"LSP request '{method}' failed for server '{self.name}': {last_error}")

    async def send_notification(self, method: str, params: Any) -> None:
        if not self.is_healthy:
            raise Exception(f"Cannot send notification to LSP server '{self.name}': server is {self._state}")

        try:
            await self._client.send_notification(method, params)
        except Exception as e:
            raise Exception(f"LSP notification '{method}' failed for server '{self.name}': {e}")

    def on_notification(self, method: str, handler: Callable[[Any], None]) -> None:
        self._notification_handlers[method] = handler

    def on_request(self, method: str, handler: Callable[[Any], Any]) -> None:
        self._request_handlers[method] = handler
        self._client.on_request(method, handler)


def with_timeout(promise: Any, ms: int, message: str) -> Any:
    async def _with_timeout():
        try:
            return await asyncio.wait_for(promise, timeout=ms / 1000)
        except asyncio.TimeoutError:
            raise Exception(message)
    return _with_timeout()