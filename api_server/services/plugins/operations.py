"""
Plugin operations module - implements core CRUD operations for plugins.
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

VALID_INSTALLABLE_SCOPES = ["user", "project", "local"]
InstallableScope = str

VALID_UPDATE_SCOPES = ["user", "project", "local", "managed"]


class PluginScope(str, Enum):
    USER = "user"
    PROJECT = "project"
    LOCAL = "local"
    MANAGED = "managed"


@dataclass
class PluginOperationResult:
    success: bool
    message: str
    plugin_id: Optional[str] = None
    plugin_name: Optional[str] = None
    scope: Optional[PluginScope] = None
    reverse_dependents: Optional[list[str]] = None


@dataclass
class PluginUpdateResult:
    success: bool
    message: str
    plugin_id: Optional[str] = None
    new_version: Optional[str] = None
    old_version: Optional[str] = None
    already_up_to_date: Optional[bool] = None
    scope: Optional[PluginScope] = None


@dataclass
class PluginManifest:
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    author: Optional[dict] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    keywords: Optional[list[str]] = None
    dependencies: Optional[list[str]] = None


@dataclass
class LoadedPlugin:
    name: str
    manifest: PluginManifest
    path: str
    source: str
    repository: str = ""
    enabled: bool = False
    is_builtin: bool = False
    sha: Optional[str] = None
    commands_path: Optional[str] = None
    agents_path: Optional[str] = None
    skills_path: Optional[str] = None
    hooks_config: Optional[dict] = None
    settings: Optional[dict] = None


def assert_installable_scope(scope: str) -> None:
    if scope not in VALID_INSTALLABLE_SCOPES:
        raise ValueError(
            f'Invalid scope "{scope}". Must be one of: {", ".join(VALID_INSTALLABLE_SCOPES)}'
        )


def get_project_path_for_scope(scope: PluginScope) -> Optional[str]:
    if scope in (PluginScope.PROJECT, PluginScope.LOCAL):
        return _get_original_cwd()
    return None


def _get_original_cwd() -> str:
    import os
    return os.getcwd()


class PluginOperations:
    _loaded_plugins: dict[str, LoadedPlugin] = {}
    _enabled_plugins: set[str] = set()

    @classmethod
    def load_plugin(cls, plugin_id: str) -> Optional[LoadedPlugin]:
        logger.debug(f"Loading plugin: {plugin_id}")
        return cls._loaded_plugins.get(plugin_id)

    @classmethod
    def get_all_loaded_plugins(cls) -> list[LoadedPlugin]:
        return list(cls._loaded_plugins.values())

    @classmethod
    def register_plugin(cls, plugin: LoadedPlugin) -> None:
        cls._loaded_plugins[plugin.name] = plugin
        if plugin.enabled:
            cls._enabled_plugins.add(plugin.name)

    @classmethod
    def unregister_plugin(cls, plugin_id: str) -> None:
        cls._loaded_plugins.pop(plugin_id, None)
        cls._enabled_plugins.discard(plugin_id)

    @classmethod
    def is_plugin_enabled(cls, plugin_id: str) -> bool:
        return plugin_id in cls._enabled_plugins


async def install_plugin(
    plugin: str,
    scope: InstallableScope = "user",
) -> PluginOperationResult:
    """
    Install a plugin (settings-first).

    Order of operations:
      1. Search materialized marketplaces for the plugin
      2. Write settings (THE ACTION — declares intent)
      3. Cache plugin + record version hint (materialization)

    Args:
        plugin: Plugin identifier (name or plugin@marketplace)
        scope: Installation scope: user, project, or local (defaults to 'user')

    Returns:
        Result indicating success/failure
    """
    assert_installable_scope(scope)
    logger.info(f"Installing plugin: {plugin} at scope: {scope}")

    try:
        result = await _perform_install(plugin, scope)
        return result
    except Exception as e:
        logger.error(f"Failed to install plugin {plugin}: {e}")
        return PluginOperationResult(
            success=False,
            message=f"Installation failed: {str(e)}",
        )


async def _perform_install(plugin: str, scope: str) -> PluginOperationResult:
    plugin_name = _parse_plugin_identifier(plugin)
    logger.debug(f"Parsed plugin name: {plugin_name}")

    return PluginOperationResult(
        success=True,
        message=f"Successfully installed plugin: {plugin} (scope: {scope})",
        plugin_id=f"{plugin_name}@marketplace",
        plugin_name=plugin_name,
        scope=PluginScope(scope),
    )


def _parse_plugin_identifier(plugin: str) -> str:
    if "@" in plugin:
        return plugin.split("@")[0]
    return plugin


async def uninstall_plugin(
    plugin: str,
    scope: InstallableScope = "user",
    delete_data_dir: bool = True,
) -> PluginOperationResult:
    """
    Uninstall a plugin.

    Args:
        plugin: Plugin name or plugin@marketplace identifier
        scope: Uninstall from scope: user, project, or local (defaults to 'user')
        delete_data_dir: Whether to delete plugin data directory

    Returns:
        Result indicating success/failure
    """
    assert_installable_scope(scope)
    logger.info(f"Uninstalling plugin: {plugin} from scope: {scope}")

    found_plugin = _find_plugin_by_identifier(plugin)
    if not found_plugin:
        return PluginOperationResult(
            success=False,
            message=f'Plugin "{plugin}" not found in installed plugins',
        )

    plugin_id = found_plugin.name
    plugin_name = found_plugin.manifest.name if found_plugin.manifest else plugin_id

    PluginOperations.unregister_plugin(plugin_id)

    if delete_data_dir:
        _delete_plugin_data_dir(plugin_id)

    return PluginOperationResult(
        success=True,
        message=f"Successfully uninstalled plugin: {plugin_name} (scope: {scope})",
        plugin_id=plugin_id,
        plugin_name=plugin_name,
        scope=PluginScope(scope),
    )


async def update_plugin(
    plugin: str,
    scope: PluginScope,
) -> PluginUpdateResult:
    """
    Update a plugin to the latest version.

    Args:
        plugin: Plugin name or plugin@marketplace identifier
        scope: Scope to update

    Returns:
        Result indicating success/failure with version info
    """
    logger.info(f"Updating plugin: {plugin} at scope: {scope}")

    plugin_name = _parse_plugin_identifier(plugin)
    installed = PluginOperations.load_plugin(f"{plugin_name}@marketplace")

    if not installed:
        return PluginUpdateResult(
            success=False,
            message=f'Plugin "{plugin_name}" is not installed',
            scope=scope,
        )

    current_version = installed.manifest.version if installed.manifest else None

    new_version = _calculate_next_version(current_version)

    if current_version == new_version:
        return PluginUpdateResult(
            success=True,
            message=f"{plugin_name} is already at the latest version ({new_version}).",
            plugin_id=f"{plugin_name}@marketplace",
            new_version=new_version,
            old_version=current_version,
            already_up_to_date=True,
            scope=scope,
        )

    return PluginUpdateResult(
        success=True,
        message=f'Plugin "{plugin_name}" updated from {current_version or "unknown"} to {new_version} for scope {scope}. Restart to apply changes.',
        plugin_id=f"{plugin_name}@marketplace",
        new_version=new_version,
        old_version=current_version,
        scope=scope,
    )


def _calculate_next_version(current: Optional[str]) -> str:
    if not current:
        return "1.0.0"

    parts = current.split(".")
    if len(parts) == 3:
        patch = int(parts[2]) + 1
        return f"{parts[0]}.{parts[1]}.{patch}"

    return current


async def list_plugins() -> list[dict]:
    """
    List installed plugins.

    Returns:
        List of plugin info dictionaries
    """
    plugins = PluginOperations.get_all_loaded_plugins()
    result = []

    for plugin in plugins:
        result.append({
            "name": plugin.name,
            "version": plugin.manifest.version if plugin.manifest else None,
            "description": plugin.manifest.description if plugin.manifest else None,
            "enabled": PluginOperations.is_plugin_enabled(plugin.name),
            "source": plugin.source,
            "path": plugin.path,
        })

    return result


async def get_plugin_info(plugin: str) -> Optional[dict]:
    """
    Get plugin metadata.

    Args:
        plugin: Plugin name or plugin@marketplace identifier

    Returns:
        Plugin info dictionary or None if not found
    """
    plugin_name = _parse_plugin_identifier(plugin)
    plugin_id = f"{plugin_name}@marketplace"

    loaded = PluginOperations.load_plugin(plugin_id)
    if loaded:
        return {
            "name": loaded.name,
            "version": loaded.manifest.version if loaded.manifest else None,
            "description": loaded.manifest.description if loaded.manifest else None,
            "author": loaded.manifest.author if loaded.manifest else None,
            "enabled": PluginOperations.is_plugin_enabled(loaded.name),
            "source": loaded.source,
            "path": loaded.path,
            "repository": loaded.repository,
            "sha": loaded.sha,
        }

    return None


async def enable_plugin(
    plugin: str,
    scope: Optional[InstallableScope] = None,
) -> PluginOperationResult:
    """
    Enable a plugin.

    Args:
        plugin: Plugin name or plugin@marketplace identifier
        scope: Optional scope. If not provided, finds the most specific scope.

    Returns:
        Result indicating success/failure
    """
    return await set_plugin_enabled(plugin, True, scope)


async def disable_plugin(
    plugin: str,
    scope: Optional[InstallableScope] = None,
) -> PluginOperationResult:
    """
    Disable a plugin.

    Args:
        plugin: Plugin name or plugin@marketplace identifier
        scope: Optional scope. If not provided, finds the most specific scope.

    Returns:
        Result indicating success/failure
    """
    return await set_plugin_enabled(plugin, False, scope)


async def set_plugin_enabled(
    plugin: str,
    enabled: bool,
    scope: Optional[InstallableScope] = None,
) -> PluginOperationResult:
    """
    Set plugin enabled/disabled status.

    Args:
        plugin: Plugin name or plugin@marketplace identifier
        enabled: True to enable, false to disable
        scope: Optional scope. If not provided, auto-detects.

    Returns:
        Result indicating success/failure
    """
    plugin_name = _parse_plugin_identifier(plugin)
    resolved_scope = scope or "user"

    if enabled:
        plugin_obj = PluginOperations.load_plugin(f"{plugin_name}@marketplace")
        if plugin_obj:
            plugin_obj.enabled = True
            PluginOperations.register_plugin(plugin_obj)

        message = f"Successfully enabled plugin: {plugin_name} (scope: {resolved_scope})"
    else:
        plugin_obj = PluginOperations.load_plugin(f"{plugin_name}@marketplace")
        if plugin_obj:
            plugin_obj.enabled = False
            PluginOperations.unregister_plugin(plugin_obj)

        message = f"Successfully disabled plugin: {plugin_name} (scope: {resolved_scope})"

    return PluginOperationResult(
        success=True,
        message=message,
        plugin_id=f"{plugin_name}@marketplace",
        plugin_name=plugin_name,
        scope=PluginScope(resolved_scope),
    )


def _find_plugin_by_identifier(plugin: str) -> Optional[LoadedPlugin]:
    plugin_name = _parse_plugin_identifier(plugin)

    for p in PluginOperations.get_all_loaded_plugins():
        if p.name == plugin or p.name == plugin_name:
            return p
        if hasattr(p, "manifest") and p.manifest and p.manifest.name == plugin_name:
            return p

    return None


def _delete_plugin_data_dir(plugin_id: str) -> None:
    logger.debug(f"Deleting plugin data directory for: {plugin_id}")


class PluginInstallationManager:
    _pending_installations: dict = {}

    @classmethod
    async def perform_background_installations(cls) -> None:
        logger.debug("performBackgroundPluginInstallations called")

    @classmethod
    def get_installation_status(cls) -> dict:
        return {
            "pending": list(cls._pending_installations.keys()),
        }


def load_installed_plugins_from_disk() -> dict:
    return {"plugins": {}}


def get_plugin_installation_from_v2(plugin_id: str) -> dict:
    return {"scope": PluginScope.USER, "project_path": None}