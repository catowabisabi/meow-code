import os
from typing import Any

from .manager import get_lsp_server_manager


def _get_file_uri(file_path: str) -> str:
    abs_path = os.path.abspath(file_path)
    return f"file:///{abs_path.replace(os.sep, '/')}"


def _position_from_line_char(file_path: str, line: int, character: int) -> dict[str, Any]:
    return {
        "line": line - 1,
        "character": character - 1,
    }


async def go_to_definition(file_path: str, line: int, character: int) -> Any | None:
    manager = get_lsp_server_manager()
    if not manager:
        return None

    uri = _get_file_uri(file_path)
    params = {
        "textDocument": {"uri": uri},
        "position": _position_from_line_char(file_path, line, character),
    }
    return await manager.send_request(file_path, "textDocument/definition", params)


async def find_references(file_path: str, line: int, character: int) -> Any | None:
    manager = get_lsp_server_manager()
    if not manager:
        return None

    uri = _get_file_uri(file_path)
    params = {
        "textDocument": {"uri": uri},
        "position": _position_from_line_char(file_path, line, character),
        "context": {"includeDeclaration": True},
    }
    return await manager.send_request(file_path, "textDocument/references", params)


async def hover(file_path: str, line: int, character: int) -> Any | None:
    manager = get_lsp_server_manager()
    if not manager:
        return None

    uri = _get_file_uri(file_path)
    params = {
        "textDocument": {"uri": uri},
        "position": _position_from_line_char(file_path, line, character),
    }
    return await manager.send_request(file_path, "textDocument/hover", params)


async def document_symbol(file_path: str) -> Any | None:
    manager = get_lsp_server_manager()
    if not manager:
        return None

    uri = _get_file_uri(file_path)
    params = {
        "textDocument": {"uri": uri},
    }
    return await manager.send_request(file_path, "textDocument/documentSymbol", params)


async def workspace_symbol(query: str) -> Any | None:
    manager = get_lsp_server_manager()
    if not manager:
        return None

    params = {"query": query}
    servers = manager.get_all_servers()
    if not servers:
        return None

    first_server = next(iter(servers.values()))
    return await first_server.send_request("workspace/symbol", params)


async def go_to_implementation(file_path: str, line: int, character: int) -> Any | None:
    manager = get_lsp_server_manager()
    if not manager:
        return None

    uri = _get_file_uri(file_path)
    params = {
        "textDocument": {"uri": uri},
        "position": _position_from_line_char(file_path, line, character),
    }
    return await manager.send_request(file_path, "textDocument/implementation", params)


async def prepare_call_hierarchy(file_path: str, line: int, character: int) -> Any | None:
    manager = get_lsp_server_manager()
    if not manager:
        return None

    uri = _get_file_uri(file_path)
    params = {
        "textDocument": {"uri": uri},
        "position": _position_from_line_char(file_path, line, character),
    }
    return await manager.send_request(file_path, "textDocument/prepareCallHierarchy", params)


async def incoming_calls(file_path: str, line: int, character: int) -> Any | None:
    manager = get_lsp_server_manager()
    if not manager:
        return None

    uri = _get_file_uri(file_path)
    prepare_params = {
        "textDocument": {"uri": uri},
        "position": _position_from_line_char(file_path, line, character),
    }
    items = await manager.send_request(file_path, "textDocument/prepareCallHierarchy", prepare_params)

    if not items or len(items) == 0:
        return None

    call_params = {"item": items[0]}
    return await manager.send_request(file_path, "callHierarchy/incomingCalls", call_params)


async def outgoing_calls(file_path: str, line: int, character: int) -> Any | None:
    manager = get_lsp_server_manager()
    if not manager:
        return None

    uri = _get_file_uri(file_path)
    prepare_params = {
        "textDocument": {"uri": uri},
        "position": _position_from_line_char(file_path, line, character),
    }
    items = await manager.send_request(file_path, "textDocument/prepareCallHierarchy", prepare_params)

    if not items or len(items) == 0:
        return None

    call_params = {"item": items[0]}
    return await manager.send_request(file_path, "callHierarchy/outgoingCalls", call_params)