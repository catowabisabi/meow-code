"""
Plugins Service for api_server.

This module provides Python implementations of the TypeScript plugin operations
from _claude_code_leaked_source_code/src/services/plugins/.

Provides:
- PluginOperations: CRUD operations for plugins (install, uninstall, update, list)
- PluginManager: Plugin lifecycle management (load, unload, reload)
- PluginInstaller: Plugin installation handling (download, extract, verify)
- Plugin configuration loading from CLAUDE.md and settings

Architecture follows the TypeScript source:
- pluginOperations.ts -> operations.py (core CRUD)
- PluginInstallationManager.ts -> installer.py (background installation)
- pluginCliCommands.ts -> cli.py (CLI wrappers, not implemented here)
"""

from .operations import (
    PluginOperations,
    PluginOperationResult,
    PluginUpdateResult,
    InstallableScope,
    VALID_INSTALLABLE_SCOPES,
    VALID_UPDATE_SCOPES,
    install_plugin,
    uninstall_plugin,
    update_plugin,
    list_plugins,
    get_plugin_info,
    enable_plugin,
    disable_plugin,
)
from .manager import (
    PluginManager,
    PluginLifecycleState,
    get_plugin_hooks,
)
from .installer import (
    PluginInstaller,
    InstallationResult,
    download_plugin,
    extract_plugin,
    verify_plugin,
    install_dependencies,
)
from .config import (
    load_plugin_config,
    get_enabled_plugins,
    get_plugin_settings,
)

__all__ = [
    # operations
    "PluginOperations",
    "PluginOperationResult",
    "PluginUpdateResult",
    "InstallableScope",
    "VALID_INSTALLABLE_SCOPES",
    "VALID_UPDATE_SCOPES",
    "install_plugin",
    "uninstall_plugin",
    "update_plugin",
    "list_plugins",
    "get_plugin_info",
    "enable_plugin",
    "disable_plugin",
    # manager
    "PluginManager",
    "PluginLifecycleState",
    "get_plugin_hooks",
    # installer
    "PluginInstaller",
    "InstallationResult",
    "download_plugin",
    "extract_plugin",
    "verify_plugin",
    "install_dependencies",
    # config
    "load_plugin_config",
    "get_enabled_plugins",
    "get_plugin_settings",
]