"""Plugin system - bridging gap with TypeScript utils/plugins/"""
import asyncio
import logging
import subprocess
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


@dataclass
class Plugin:
    name: str
    version: str
    source: str
    install_path: str
    enabled: bool = True
    metadata: Dict[str, Any] = None


class PluginSource(Enum):
    NPM = "npm"
    GIT = "git"
    LOCAL = "local"
    MARKETPLACE = "marketplace"


class DependencyResolver:
    """
    Dependency resolution for plugins.
    
    TypeScript equivalent: dependencyResolver.ts
    Python gap: No dependency resolution equivalent.
    """
    
    def __init__(self):
        self._cache: Dict[str, List[str]] = {}
    
    def resolve(self, plugin_name: str, version: str = "latest") -> Optional[str]:
        cache_key = f"{plugin_name}@{version}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = subprocess.run(
            ["npm", "view", plugin_name, "version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            resolved_version = result.stdout.strip()
            self._cache[cache_key] = resolved_version
            return resolved_version
        
        return None
    
    def resolve_dependencies(self, package_json: Dict[str, Any]) -> List[str]:
        deps = package_json.get("dependencies", {})
        return list(deps.keys())


class PluginLoader:
    """
    Plugin loading with validation.
    
    TypeScript equivalent: pluginLoader.ts
    Python gap: Git/npm/validation all missing.
    """
    
    def __init__(
        self,
        plugin_dir: str = "~/.claude/plugins",
        marketplace_dir: Optional[str] = None
    ):
        self.plugin_dir = Path(plugin_dir).expanduser()
        self.marketplace_dir = Path(marketplace_dir).expanduser() if marketplace_dir else None
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {}
    
    async def load_plugin(self, plugin: Plugin) -> bool:
        try:
            plugin_path = Path(plugin.install_path)
            
            if not plugin_path.exists():
                logger.error(f"Plugin path does not exist: {plugin_path}")
                return False
            
            manifest = await self._load_manifest(plugin_path)
            
            if not await self._validate_plugin(manifest):
                return False
            
            await self._execute_install(plugin_path, manifest)
            
            self._plugins[plugin.name] = plugin
            await self._register_hooks(plugin.name, plugin_path, manifest)
            
            logger.info(f"Loaded plugin: {plugin.name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin.name}: {e}")
            return False
    
    async def _load_manifest(self, plugin_path: Path) -> Dict[str, Any]:
        import json
        
        manifest_path = plugin_path / "manifest.json"
        
        if manifest_path.exists():
            with open(manifest_path) as f:
                return json.load(f)
        
        package_json_path = plugin_path / "package.json"
        if package_json_path.exists():
            with open(package_json_path) as f:
                return json.load(f)
        
        return {}
    
    async def _validate_plugin(self, manifest: Dict[str, Any]) -> bool:
        required_fields = ["name", "version"]
        
        for field in required_fields:
            if field not in manifest:
                logger.error(f"Plugin missing required field: {field}")
                return False
        
        return True
    
    async def _execute_install(self, plugin_path: Path, manifest: Dict[str, Any]) -> None:
        if (plugin_path / "package.json").exists():
            subprocess.run(
                ["npm", "install", "--production"],
                cwd=plugin_path,
                capture_output=True
            )
    
    async def _register_hooks(
        self,
        plugin_name: str,
        plugin_path: Path,
        manifest: Dict[str, Any]
    ) -> None:
        hooks = manifest.get("hooks", {})
        
        for hook_name, hook_path in hooks.items():
            if hook_name not in self._hooks:
                self._hooks[hook_name] = []
            self._hooks[hook_name].append(lambda: plugin_path / hook_path)
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)
    
    def list_plugins(self) -> List[Plugin]:
        return list(self._plugins.values())
    
    def unload_plugin(self, name: str) -> bool:
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False


class MarketplaceManager:
    """
    Plugin marketplace management.
    
    TypeScript equivalent: marketplaceManager.ts
    Python gap: No marketplace management equivalent.
    """
    
    def __init__(self):
        self._registry: Dict[str, Plugin] = {}
    
    async def fetch_marketplace_list(self) -> List[Dict[str, Any]]:
        return []
    
    async def install_from_marketplace(self, plugin_name: str) -> bool:
        return False
    
    def get_registered_plugins(self) -> List[Plugin]:
        return list(self._registry.values())


_plugin_loader: Optional[PluginLoader] = None


def get_plugin_loader() -> PluginLoader:
    global _plugin_loader
    if _plugin_loader is None:
        _plugin_loader = PluginLoader()
    return _plugin_loader
