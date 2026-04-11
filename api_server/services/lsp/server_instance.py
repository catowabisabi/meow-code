"""LSP Server Instance - manages single LSP server lifecycle with state machine."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from api_server.services.lsp.client import create_lsp_client


LSP_ERROR_CONTENT_MODIFIED = -32801
MAX_RETRIES_FOR_TRANSIENT_ERRORS = 3
RETRY_BASE_DELAY_MS = 500


@dataclass
class ScopedLspServerConfig:
    command: str
    args: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    workspace_folder: Optional[str] = None
    initialization_options: Optional[Dict[str, Any]] = None
    startup_timeout: Optional[int] = None
    max_restarts: Optional[int] = None
    extension_to_language: Dict[str, str] = field(default_factory=dict)


LspServerState = str
LSP_SERVER_STATES = ["stopped", "starting", "running", "stopping", "error"]


class LSPServerInstance:
    def __init__(
        self,
        name: str,
        config: ScopedLspServerConfig,
    ):
        self._name = name
        self._config = config
        self._state: LspServerState = "stopped"
        self._start_time: Optional[datetime] = None
        self._last_error: Optional[Exception] = None
        self._restart_count = 0
        self._crash_recovery_count = 0
        self._client = create_lsp_client(
            name,
            on_crash=lambda error: self._handle_crash(error),
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def config(self) -> ScopedLspServerConfig:
        return self._config

    @property
    def state(self) -> LspServerState:
        return self._state

    @property
    def start_time(self) -> Optional[datetime]:
        return self._start_time

    @property
    def last_error(self) -> Optional[Exception]:
        return self._last_error

    @property
    def restart_count(self) -> int:
        return self._restart_count

    def _handle_crash(self, error: Exception) -> None:
        self._state = "error"
        self._last_error = error
        self._crash_recovery_count += 1

    async def start(self) -> None:
        if self._state in ("running", "starting"):
            return

        max_restarts = self._config.max_restarts if self._config.max_restarts is not None else 3

        if self._state == "error" and self._crash_recovery_count > max_restarts:
            error = Exception(
                f"LSP server '{self._name}' exceeded max crash recovery attempts ({max_restarts})"
            )
            self._last_error = error
            raise error

        try:
            self._state = "starting"

            await self._client.start(
                self._config.command,
                self._config.args or [],
                {"env": self._config.env, "cwd": self._config.workspace_folder},
            )

            workspace_folder = self._config.workspace_folder or str(Path.cwd())
            workspace_uri = Path(workspace_folder).as_uri()

            init_params = {
                "processId": None,
                "initializationOptions": self._config.initialization_options or {},
                "workspaceFolders": [
                    {
                        "uri": workspace_uri,
                        "name": Path(workspace_folder).name,
                    }
                ],
                "rootPath": workspace_folder,
                "rootUri": workspace_uri,
                "capabilities": {
                    "workspace": {
                        "configuration": False,
                        "workspaceFolders": False,
                    },
                    "textDocument": {
                        "synchronization": {
                            "dynamicRegistration": False,
                            "willSave": False,
                            "willSaveWaitUntil": False,
                            "didSave": True,
                        },
                        "publishDiagnostics": {
                            "relatedInformation": True,
                            "tagSupport": {"valueSet": [1, 2]},
                            "versionSupport": False,
                            "codeDescriptionSupport": True,
                            "dataSupport": False,
                        },
                        "hover": {
                            "dynamicRegistration": False,
                            "contentFormat": ["markdown", "plaintext"],
                        },
                        "definition": {
                            "dynamicRegistration": False,
                            "linkSupport": True,
                        },
                        "references": {"dynamicRegistration": False},
                        "documentSymbol": {
                            "dynamicRegistration": False,
                            "hierarchicalDocumentSymbolSupport": True,
                        },
                        "callHierarchy": {"dynamicRegistration": False},
                    },
                    "general": {"positionEncodings": ["utf-16"]},
                },
            }

            init_promise = self._client.initialize(init_params)

            if self._config.startup_timeout is not None:
                init_promise = asyncio.wait_for(
                    init_promise,
                    timeout=self._config.startup_timeout / 1000.0,
                )

            await init_promise

            self._state = "running"
            self._start_time = datetime.now()
            self._crash_recovery_count = 0

        except Exception as error:
            try:
                await self._client.stop()
            except Exception:
                pass
            self._state = "error"
            self._last_error = error if isinstance(error, Exception) else Exception(str(error))
            raise

    async def stop(self) -> None:
        if self._state in ("stopped", "stopping"):
            return

        try:
            self._state = "stopping"
            await self._client.stop()
            self._state = "stopped"
        except Exception as error:
            self._state = "error"
            self._last_error = error if isinstance(error, Exception) else Exception(str(error))
            raise

    async def restart(self) -> None:
        try:
            await self.stop()
        except Exception as error:
            raise Exception(f"Failed to stop LSP server '{self._name}' during restart: {error}")

        self._restart_count += 1

        max_restarts = self._config.max_restarts if self._config.max_restarts is not None else 3
        if self._restart_count > max_restarts:
            raise Exception(
                f"Max restart attempts ({max_restarts}) exceeded for server '{self._name}'"
            )

        try:
            await self.start()
        except Exception as error:
            raise Exception(
                f"Failed to start LSP server '{self._name}' during restart "
                f"(attempt {self._restart_count}/{max_restarts}): {error}"
            )

    def is_healthy(self) -> bool:
        return self._state == "running" and self._client.is_initialized

    async def send_request(self, method: str, params: Any) -> Any:
        if not self.is_healthy():
            error_msg = f"Cannot send request to LSP server '{self._name}': server is {self._state}"
            if self._last_error:
                error_msg += f", last error: {self._last_error}"
            raise Exception(error_msg)

        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES_FOR_TRANSIENT_ERRORS + 1):
            try:
                return await self._client.send_request(method, params)
            except Exception as error:
                last_error = error if isinstance(error, Exception) else Exception(str(error))

                error_code = getattr(error, "code", None)
                is_content_modified = isinstance(error_code, int) and error_code == LSP_ERROR_CONTENT_MODIFIED

                if is_content_modified and attempt < MAX_RETRIES_FOR_TRANSIENT_ERRORS:
                    delay = RETRY_BASE_DELAY_MS * (2 ** attempt)
                    await asyncio.sleep(delay / 1000.0)
                    continue

                break

        raise Exception(
            f"LSP request '{method}' failed for server '{self._name}': "
            f"{last_error.message if last_error else 'unknown error'}"
        )

    async def send_notification(self, method: str, params: Any) -> None:
        if not self.is_healthy():
            raise Exception(
                f"Cannot send notification to LSP server '{self._name}': server is {self._state}"
            )

        try:
            await self._client.send_notification(method, params)
        except Exception as error:
            raise Exception(
                f"LSP notification '{method}' failed for server '{self._name}': {error}"
            )

    def on_notification(self, method: str, handler: Callable[[Any], None]) -> None:
        self._client.on_notification(method, handler)

    def on_request(self, method: str, handler: Callable[[Any], Any]) -> None:
        self._client.on_request(method, handler)


def create_lsp_server_instance(
    name: str,
    config: ScopedLspServerConfig,
) -> LSPServerInstance:
    if config.max_restarts is not None:
        pass
    return LSPServerInstance(name=name, config=config)
