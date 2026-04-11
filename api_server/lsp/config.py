from typing import Any

from .types import ScopedLspServerConfig


_server_configs: dict[str, ScopedLspServerConfig] = {}


def _load_configs() -> dict[str, ScopedLspServerConfig]:
    return {}


async def get_all_lsp_servers() -> dict[str, ScopedLspServerConfig]:
    global _server_configs
    if not _server_configs:
        _server_configs = _load_configs()
    return _server_configs


def get_lsp_server_config(language: str) -> ScopedLspServerConfig | None:
    for config in _server_configs.values():
        if language in config.extension_to_language.values():
            return config
    return None


def register_lsp_server(config: ScopedLspServerConfig) -> None:
    global _server_configs
    _server_configs[config.name] = config


def clear_lsp_servers() -> None:
    global _server_configs
    _server_configs = {}