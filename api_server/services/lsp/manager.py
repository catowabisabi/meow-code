"""LSP Server Manager - multi-server routing by file extension.

Ported from TypeScript manager.ts to include singleton management,
initialization state machine, and lifecycle functions.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from api_server.services.lsp.server_instance import LSPServerInstance, ScopedLspServerConfig


logger = logging.getLogger(__name__)


class InitializationState(str, Enum):
    """Initialization state of the LSP server manager."""
    NOT_STARTED = "not-started"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class InitializationStatus:
    """Status of LSP server manager initialization."""
    status: InitializationState
    error: Optional[Exception] = None


# Module-level singleton state
_manager: Optional["LSPServerManager"] = None
_state: InitializationState = InitializationState.NOT_STARTED
_init_error: Optional[Exception] = None
_initialization_promise: Optional[asyncio.Task] = None
_initialization_generation: int = 0


def _reset_lsp_manager_for_testing() -> None:
    """
    Test-only sync reset. shutdownLspServerManager() is async and tears down
    real connections; this only clears the module-scope singleton state so
    reinitializeLspServerManager() early-returns on 'not-started' in downstream
    tests on the same shard.
    """
    global _manager, _state, _init_error, _initialization_promise, _initialization_generation
    _state = InitializationState.NOT_STARTED
    _init_error = None
    _initialization_promise = None
    _initialization_generation += 1


def get_lsp_server_manager() -> Optional["LSPServerManager"]:
    """
    Get the singleton LSP server manager instance.
    
    Returns None if not yet initialized, initialization failed, or still pending.
    
    Callers should check for None and handle gracefully, as initialization happens
    asynchronously during startup. Use getInitializationStatus() to distinguish
    between pending, failed, and not-started states.
    """
    if _state == InitializationState.FAILED:
        return None
    return _manager


def get_initialization_status() -> InitializationStatus:
    """
    Get the current initialization status of the LSP server manager.
    
    Returns:
        InitializationStatus with current state and error (if failed)
    """
    if _state == InitializationState.FAILED:
        return InitializationStatus(
            status=_state,
            error=_init_error or Exception("Initialization failed"),
        )
    if _state == InitializationState.NOT_STARTED:
        return InitializationStatus(status=_state, error=None)
    if _state == InitializationState.PENDING:
        return InitializationStatus(status=_state, error=None)
    return InitializationStatus(status=_state, error=None)


def is_lsp_connected() -> bool:
    """
    Check whether at least one language server is connected and healthy.
    
    Backs LSPTool.isEnabled().
    """
    if _state == InitializationState.FAILED:
        return False
    manager = get_lsp_server_manager()
    if not manager:
        return False
    servers = manager.get_all_servers()
    if len(servers) == 0:
        return False
    for server in servers.values():
        if server.state != "error":
            return True
    return False


async def wait_for_initialization() -> None:
    """
    Wait for LSP server manager initialization to complete.
    
    Returns immediately if initialization has already completed (success or failure).
    If initialization is pending, waits for it to complete.
    If initialization hasn't started, returns immediately.
    """
    if _state == InitializationState.SUCCESS or _state == InitializationState.FAILED:
        return

    if _state == InitializationState.PENDING and _initialization_promise:
        await _initialization_promise


async def _do_initialize() -> None:
    """Internal async initialization implementation."""
    global _manager, _state, _init_error

    try:
        if _manager is None:
            _manager = LSPServerManager()
        await _manager.initialize({})
        _state = InitializationState.SUCCESS
        logger.debug("LSP server manager initialized successfully")

        # Register passive notification handlers for diagnostics
        from api_server.services.lsp.passive_feedback import register_lsp_notification_handlers
        if _manager:
            register_lsp_notification_handlers(_manager)
    except Exception as e:
        _state = InitializationState.FAILED
        _init_error = e
        _manager = None
        logger.error(f"Failed to initialize LSP server manager: {e}")


def initialize_lsp_server_manager() -> None:
    """
    Initialize the LSP server manager singleton.
    
    This function is called during startup. It synchronously creates
    the manager instance, then starts async initialization (loading LSP configs)
    in the background without blocking the startup process.
    
    Safe to call multiple times - will only initialize once (idempotent).
    However, if initialization previously failed, calling again will retry.
    """
    global _manager, _state, _init_error, _initialization_promise, _initialization_generation

    logger.debug("[LSP MANAGER] initialize_lsp_server_manager() called")

    # Skip if already initialized or currently initializing
    if _manager is not None and _state != InitializationState.FAILED:
        logger.debug("[LSP MANAGER] Already initialized or initializing, skipping")
        return

    # Reset state for retry if previous initialization failed
    if _state == InitializationState.FAILED:
        _manager = None
        _init_error = None

    # Create the manager instance and mark as pending
    _manager = LSPServerManager()
    _state = InitializationState.PENDING
    logger.debug("[LSP MANAGER] Created manager instance, state=pending")

    # Increment generation to invalidate any pending initializations
    current_generation = _initialization_generation + 1
    _initialization_generation = current_generation
    logger.debug(f"[LSP MANAGER] Starting async initialization (generation {current_generation})")

    # Start initialization asynchronously without blocking
    # Store the promise so callers can await it via waitForInitialization()
    _initialization_promise = asyncio.create_task(_do_initialize())


def reinitialize_lsp_server_manager() -> None:
    """
    Force re-initialization of the LSP server manager, even after a prior
    successful init.
    
    Called from refreshActivePlugins() after plugin caches are cleared,
    so newly-loaded plugin LSP servers are picked up.
    
    Safe to call when no LSP plugins changed: initialize() is just config
    parsing (servers are lazy-started on first use). Also safe during pending
    init: the generation counter invalidates the in-flight promise.
    """
    global _manager, _state, _init_error, _initialization_promise, _initialization_generation

    if _state == InitializationState.NOT_STARTED:
        # initializeLspServerManager() was never called (e.g. headless subcommand
        # path). Don't start it now.
        return

    logger.debug("[LSP MANAGER] reinitialize_lsp_server_manager() called")

    # Best-effort shutdown of any running servers on the old instance so
    # /reload-plugins doesn't leak child processes. Fire-and-forget: the
    # primary use case has 0 servers so this is usually a no-op.
    if _manager:
        async def shutdown_old():
            try:
                await _manager.shutdown()
            except Exception as e:
                logger.debug(f"[LSP MANAGER] old instance shutdown during reinit failed: {e}")
        asyncio.create_task(shutdown_old())

    # Force the idempotence check in initializeLspServerManager() to fall
    # through. Generation counter handles invalidating any in-flight init.
    _manager = None
    _state = InitializationState.NOT_STARTED
    _init_error = None

    initialize_lsp_server_manager()


async def shutdown_lsp_server_manager() -> None:
    """
    Shutdown the LSP server manager and clean up resources.
    
    This should be called during shutdown. Stops all running LSP servers
    and clears internal state. Safe to call when not initialized (no-op).
    
    NOTE: Errors during shutdown are logged for monitoring but NOT propagated
    to the caller. State is always cleared even if shutdown fails, to prevent
    resource accumulation. This is acceptable during application exit when
    recovery is not possible.
    """
    global _manager, _state, _init_error, _initialization_promise, _initialization_generation

    if _manager is None:
        return

    try:
        await _manager.shutdown()
        logger.debug("LSP server manager shut down successfully")
    except Exception as e:
        logger.error(f"Failed to shutdown LSP server manager: {e}")
    finally:
        _manager = None
        _state = InitializationState.NOT_STARTED
        _init_error = None
        _initialization_promise = None
        _initialization_generation += 1


class LSPServerManager:
    def __init__(self):
        self._servers: Dict[str, LSPServerInstance] = {}
        self._extension_map: Dict[str, List[str]] = {}
        self._opened_files: Dict[str, str] = {}

    async def initialize(self, server_configs: Dict[str, ScopedLspServerConfig]) -> None:
        for server_name, config in server_configs.items():
            if not config.command:
                raise Exception(f"Server {server_name} missing required 'command' field")

            if not config.extension_to_language or len(config.extension_to_language) == 0:
                raise Exception(
                    f"Server {server_name} missing required 'extension_to_language' field"
                )

            file_extensions = list(config.extension_to_language.keys())
            for ext in file_extensions:
                normalized = ext.lower()
                if normalized not in self._extension_map:
                    self._extension_map[normalized] = []
                if server_name not in self._extension_map[normalized]:
                    self._extension_map[normalized].append(server_name)

            from api_server.services.lsp.server_instance import create_lsp_server_instance
            instance = create_lsp_server_instance(server_name, config)
            self._servers[server_name] = instance

            instance.on_request("workspace/configuration", self._handle_workspace_configuration)

    def _handle_workspace_configuration(
        self, params: Dict[str, Any]
    ) -> List[Optional[Dict[str, Any]]]:
        items = params.get("items", [])
        return [None] * len(items)

    async def shutdown(self) -> None:
        to_stop = [
            (name, server)
            for name, server in self._servers.items()
            if server.state in ("running", "error")
        ]

        results = []
        for name, server in to_stop:
            try:
                await server.stop()
                results.append((name, None))
            except Exception as e:
                results.append((name, str(e)))

        errors = [f"{name}: {err}" for name, err in results if err]
        if errors:
            raise Exception(f"Failed to stop {len(errors)} LSP server(s): {'; '.join(errors)}")

        self._servers.clear()
        self._extension_map.clear()
        self._opened_files.clear()

    def get_server_for_file(self, file_path: str) -> Optional[LSPServerInstance]:
        ext = Path(file_path).suffix.lower()
        server_names = self._extension_map.get(ext, [])

        if not server_names:
            return None

        server_name = server_names[0]
        return self._servers.get(server_name)

    async def ensure_server_started(self, file_path: str) -> Optional[LSPServerInstance]:
        server = self.get_server_for_file(file_path)
        if not server:
            return None

        if server.state in ("stopped", "error"):
            await server.start()

        return server

    async def send_request(
        self, file_path: str, method: str, params: Any
    ) -> Optional[Any]:
        server = await self.ensure_server_started(file_path)
        if not server:
            return None

        return await server.send_request(method, params)

    def get_all_servers(self) -> Dict[str, LSPServerInstance]:
        return self._servers

    async def open_file(self, file_path: str, content: str) -> None:
        server = await self.ensure_server_started(file_path)
        if not server:
            return

        file_uri = Path(file_path).resolve().as_uri()

        if self._opened_files.get(file_uri) == server.name:
            return

        ext = Path(file_path).suffix.lower()
        language_id = server.config.extension_to_language.get(ext, "plaintext")

        await server.send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": file_uri,
                "languageId": language_id,
                "version": 1,
                "text": content,
            }
        })
        self._opened_files[file_uri] = server.name

    async def change_file(self, file_path: str, content: str) -> None:
        server = self.get_server_for_file(file_path)
        if not server or server.state != "running":
            await self.open_file(file_path, content)
            return

        file_uri = Path(file_path).resolve().as_uri()

        if self._opened_files.get(file_uri) != server.name:
            await self.open_file(file_path, content)
            return

        await server.send_notification("textDocument/didChange", {
            "textDocument": {
                "uri": file_uri,
                "version": 1,
            },
            "contentChanges": [{"text": content}],
        })

    async def save_file(self, file_path: str) -> None:
        server = self.get_server_for_file(file_path)
        if not server or server.state != "running":
            return

        file_uri = Path(file_path).resolve().as_uri()

        await server.send_notification("textDocument/didSave", {
            "textDocument": {"uri": file_uri}
        })

    async def close_file(self, file_path: str) -> None:
        server = self.get_server_for_file(file_path)
        if not server or server.state != "running":
            return

        file_uri = Path(file_path).resolve().as_uri()

        await server.send_notification("textDocument/didClose", {
            "textDocument": {"uri": file_uri}
        })
        self._opened_files.pop(file_uri, None)

    def is_file_open(self, file_path: str) -> bool:
        file_uri = Path(file_path).resolve().as_uri()
        return file_uri in self._opened_files


def create_lsp_server_manager() -> LSPServerManager:
    return LSPServerManager()
