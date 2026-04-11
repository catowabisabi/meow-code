import asyncio
import os
from typing import Any

from .config import get_all_lsp_servers
from .server_instance import LSPServerInstance


class LSPServerManager:
    def __init__(self):
        self._servers: dict[str, LSPServerInstance] = {}
        self._extension_map: dict[str, list[str]] = {}
        self._opened_files: dict[str, str] = {}

    async def initialize(self) -> None:
        try:
            server_configs = await get_all_lsp_servers()
        except Exception as e:
            raise Exception(f"Failed to load LSP server configuration: {e}")

        for server_name, config in server_configs.items():
            try:
                if not config.command:
                    raise Exception(f"Server {server_name} missing required 'command' field")
                if not config.extension_to_language or len(config.extension_to_language) == 0:
                    raise Exception(f"Server {server_name} missing required 'extensionToLanguage' field")

                for ext in config.extension_to_language.keys():
                    normalized = ext.lower()
                    if normalized not in self._extension_map:
                        self._extension_map[normalized] = []
                    self._extension_map[normalized].append(server_name)

                instance = LSPServerInstance(server_name, config)
                self._servers[server_name] = instance

                instance.on_request("workspace/configuration", self._handle_workspace_configuration)

            except Exception as e:
                continue

    async def shutdown(self) -> None:
        to_stop = [(name, server) for name, server in self._servers.items() if server.state == "running" or server.state == "error"]
        
        results = await asyncio.gather(*[server.stop() for _, server in to_stop], return_exceptions=True)

        self._servers.clear()
        self._extension_map.clear()
        self._opened_files.clear()

    def get_server_for_file(self, file_path: str) -> LSPServerInstance | None:
        ext = os.path.splitext(file_path)[1].lower()
        server_names = self._extension_map.get(ext)

        if not server_names or len(server_names) == 0:
            return None

        server_name = server_names[0]
        return self._servers.get(server_name)

    async def ensure_server_started(self, file_path: str) -> LSPServerInstance | None:
        server = self.get_server_for_file(file_path)
        if not server:
            return None

        if server.state == "stopped" or server.state == "error":
            try:
                await server.start()
            except Exception as e:
                raise Exception(f"Failed to start LSP server for file {file_path}: {e}")

        return server

    async def send_request(self, file_path: str, method: str, params: Any) -> Any | None:
        server = await self.ensure_server_started(file_path)
        if not server:
            return None

        try:
            return await server.send_request(method, params)
        except Exception as e:
            raise Exception(f"LSP request failed for file {file_path}, method '{method}': {e}")

    def get_all_servers(self) -> dict[str, LSPServerInstance]:
        return self._servers

    async def open_file(self, file_path: str, content: str) -> None:
        server = await self.ensure_server_started(file_path)
        if not server:
            return

        file_uri = _path_to_file_url(os.path.abspath(file_path))

        if self._opened_files.get(file_uri) == server.name:
            return

        ext = os.path.splitext(file_path)[1].lower()
        language_id = server.config.extension_to_language.get(ext, "plaintext")

        try:
            await server.send_notification("textDocument/didOpen", {
                "textDocument": {"uri": file_uri, "languageId": language_id, "version": 1, "text": content}
            })
            self._opened_files[file_uri] = server.name
        except Exception as e:
            raise Exception(f"Failed to sync file open {file_path}: {e}")

    async def change_file(self, file_path: str, content: str) -> None:
        server = self.get_server_for_file(file_path)
        if not server or server.state != "running":
            return self.open_file(file_path, content)

        file_uri = _path_to_file_url(os.path.abspath(file_path))

        if self._opened_files.get(file_uri) != server.name:
            return self.open_file(file_path, content)

        try:
            await server.send_notification("textDocument/didChange", {
                "textDocument": {"uri": file_uri, "version": 1},
                "contentChanges": [{"text": content}]
            })
        except Exception as e:
            raise Exception(f"Failed to sync file change {file_path}: {e}")

    async def save_file(self, file_path: str) -> None:
        server = self.get_server_for_file(file_path)
        if not server or server.state != "running":
            return

        try:
            await server.send_notification("textDocument/didSave", {
                "textDocument": {"uri": _path_to_file_url(os.path.abspath(file_path))}
            })
        except Exception as e:
            raise Exception(f"Failed to sync file save {file_path}: {e}")

    async def close_file(self, file_path: str) -> None:
        server = self.get_server_for_file(file_path)
        if not server or server.state != "running":
            return

        file_uri = _path_to_file_url(os.path.abspath(file_path))

        try:
            await server.send_notification("textDocument/didClose", {
                "textDocument": {"uri": file_uri}
            })
            self._opened_files.pop(file_uri, None)
        except Exception as e:
            raise Exception(f"Failed to sync file close {file_path}: {e}")

    def is_file_open(self, file_path: str) -> bool:
        file_uri = _path_to_file_url(os.path.abspath(file_path))
        return file_uri in self._opened_files

    def _handle_workspace_configuration(self, params: dict[str, Any]) -> list:
        items = params.get("items", [])
        return [None for _ in items]


def _path_to_file_url(path: str) -> str:
    if os.path.isabs(path):
        return f"file:///{path.replace(os.sep, '/')}"
    else:
        return f"file://{os.path.abspath(path).replace(os.sep, '/')}"