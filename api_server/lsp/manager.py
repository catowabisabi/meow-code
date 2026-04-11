import asyncio
from typing import Any

from .server_manager import LSPServerManager
from .types import InitializationState, InitializationStatus


_manager: LSPServerManager | None = None
_state: InitializationState = InitializationState.NOT_STARTED
_init_error: Exception | None = None
_initialization_promise: asyncio.Task | None = None


def get_lsp_server_manager() -> LSPServerManager | None:
    if _state == InitializationState.FAILED:
        return None
    return _manager


def get_initialization_status() -> InitializationStatus:
    if _state == InitializationState.FAILED:
        return InitializationStatus(status=_state, error=_init_error)
    return InitializationStatus(status=_state, error=None)


def is_lsp_connected() -> bool:
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
    if _state == InitializationState.SUCCESS or _state == InitializationState.FAILED:
        return

    if _state == InitializationState.PENDING and _initialization_promise:
        await _initialization_promise


async def _do_initialize() -> None:
    global _manager, _state, _init_error

    try:
        _manager = LSPServerManager()
        await _manager.initialize()
        _state = InitializationState.SUCCESS
    except Exception as e:
        _state = InitializationState.FAILED
        _init_error = e
        _manager = None


def initialize_lsp_server_manager() -> None:
    global _manager, _state, _init_error, _initialization_promise

    if _manager is not None and _state != InitializationState.FAILED:
        return

    if _state == InitializationState.FAILED:
        _manager = None
        _init_error = None

    _manager = LSPServerManager()
    _state = InitializationState.PENDING
    _initialization_promise = asyncio.create_task(_do_initialize())


async def shutdown_lsp_server_manager() -> None:
    global _manager, _state, _init_error, _initialization_promise

    if _manager is None:
        return

    try:
        await _manager.shutdown()
    except Exception:
        pass
    finally:
        _manager = None
        _state = InitializationState.NOT_STARTED
        _init_error = None
        _initialization_promise = None