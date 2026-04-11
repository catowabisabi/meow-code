import importlib.util
import logging
import sys
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PluginLifecycleState:
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    UNLOADING = "unloading"


class PluginManager:
    _instance: Optional["PluginManager"] = None
    _plugins: dict[str, Any] = {}
    _hooks: dict[str, list] = {}
    _state: dict[str, str] = {}

    def __new__(cls) -> "PluginManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = {}
            cls._instance._hooks = {}
            cls._instance._state = {}
        return cls._instance

    def load_plugin(self, plugin_id: str, plugin_path: str) -> bool:
        logger.info(f"Loading plugin: {plugin_id} from {plugin_path}")
        self._state[plugin_id] = PluginLifecycleState.LOADING

        try:
            spec = importlib.util.spec_from_file_location(plugin_id, plugin_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load plugin from {plugin_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_id] = module
            spec.loader.exec_module(module)

            self._plugins[plugin_id] = module
            self._state[plugin_id] = PluginLifecycleState.LOADED
            logger.info(f"Successfully loaded plugin: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            self._state[plugin_id] = PluginLifecycleState.FAILED
            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        logger.info(f"Unloading plugin: {plugin_id}")
        self._state[plugin_id] = PluginLifecycleState.UNLOADING

        try:
            if plugin_id in self._plugins:
                del self._plugins[plugin_id]

            if plugin_id in sys.modules:
                del sys.modules[plugin_id]

            self._unregister_hooks(plugin_id)
            self._state[plugin_id] = PluginLifecycleState.UNLOADED
            logger.info(f"Successfully unloaded plugin: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            self._state[plugin_id] = PluginLifecycleState.FAILED
            return False

    def reload_plugin(self, plugin_id: str) -> bool:
        logger.info(f"Reloading plugin: {plugin_id}")

        plugin = self._plugins.get(plugin_id)
        if not plugin:
            logger.warning(f"Plugin {plugin_id} not found for reload")
            return False

        plugin_path = getattr(plugin, "__file__", None)
        if not plugin_path:
            logger.error(f"Cannot determine plugin path for {plugin_id}")
            return False

        self.unload_plugin(plugin_id)
        return self.load_plugin(plugin_id, plugin_path)

    def get_plugin_hooks(self, plugin_id: str) -> list:
        return self._hooks.get(plugin_id, [])

    def get_all_hooks(self) -> dict[str, list]:
        return dict(self._hooks)

    def register_hook(self, plugin_id: str, hook_name: str, hook_func: Any) -> None:
        if plugin_id not in self._hooks:
            self._hooks[plugin_id] = []
        self._hooks[plugin_id].append({"name": hook_name, "func": hook_func})
        logger.debug(f"Registered hook {hook_name} for plugin {plugin_id}")

    def _unregister_hooks(self, plugin_id: str) -> None:
        if plugin_id in self._hooks:
            del self._hooks[plugin_id]

    def get_plugin_state(self, plugin_id: str) -> str:
        return self._state.get(plugin_id, PluginLifecycleState.UNLOADED)

    def get_loaded_plugins(self) -> list[str]:
        return list(self._plugins.keys())

    def is_plugin_loaded(self, plugin_id: str) -> bool:
        return plugin_id in self._plugins

    def get_plugin(self, plugin_id: str) -> Optional[Any]:
        return self._plugins.get(plugin_id)


def get_plugin_hooks(plugin_id: str) -> list:
    manager = PluginManager()
    return manager.get_plugin_hooks(plugin_id)