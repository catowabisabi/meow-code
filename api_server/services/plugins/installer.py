import hashlib
import logging
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class InstallationResult:
    success: bool
    message: str
    install_path: Optional[str] = None
    version: Optional[str] = None
    plugin_id: Optional[str] = None


class PluginInstaller:
    def __init__(self, cache_dir: Optional[str] = None):
        self._cache_dir = cache_dir or self._get_default_cache_dir()

    def _get_default_cache_dir(self) -> str:
        cache_base = os.path.expanduser("~/.claude/plugins")
        os.makedirs(cache_base, exist_ok=True)
        return cache_base

    async def download_plugin(self, plugin_id: str, source: str) -> str:
        logger.info(f"Downloading plugin: {plugin_id} from {source}")

        try:
            temp_dir = tempfile.mkdtemp(prefix="plugin_download_")

            if source.startswith("npm://"):
                package_name = source[6:]
                return await self._download_from_npm(package_name, temp_dir)
            elif source.startswith("github:"):
                return await self._download_from_github(source, temp_dir)
            else:
                logger.warning(f"Unknown source type for {plugin_id}, using placeholder")
                return temp_dir

        except Exception as e:
            logger.error(f"Failed to download plugin {plugin_id}: {e}")
            raise

    async def _download_from_npm(self, package_name: str, temp_dir: str) -> str:
        logger.debug(f"Downloading from npm: {package_name}")
        logger.info(f"npm download not implemented - stub for: {package_name}")
        return temp_dir

    async def _download_from_github(self, source: str, temp_dir: str) -> str:
        logger.debug(f"Downloading from github: {source}")
        logger.info(f"github download not implemented - stub for: {source}")
        return temp_dir

    async def extract_plugin(self, archive_path: str, dest_dir: str) -> str:
        logger.info(f"Extracting plugin from {archive_path} to {dest_dir}")

        try:
            os.makedirs(dest_dir, exist_ok=True)

            if archive_path.endswith(".zip"):
                return await self._extract_zip(archive_path, dest_dir)
            elif archive_path.endswith(".tar.gz") or archive_path.endswith(".tgz"):
                return await self._extract_tar(archive_path, dest_dir)
            else:
                logger.warning(f"Unknown archive format: {archive_path}")
                return dest_dir

        except Exception as e:
            logger.error(f"Failed to extract plugin: {e}")
            raise

    async def _extract_zip(self, zip_path: str, dest_dir: str) -> str:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
        return dest_dir

    async def _extract_tar(self, tar_path: str, dest_dir: str) -> str:
        import tarfile
        with tarfile.open(tar_path, "r:gz") as tf:
            tf.extractall(dest_dir)
        return dest_dir

    def verify_plugin(self, plugin_path: str) -> bool:
        logger.info(f"Verifying plugin at: {plugin_path}")

        plugin_json = Path(plugin_path) / ".claude-plugin" / "plugin.json"
        if plugin_json.exists():
            logger.debug(f"Found plugin manifest: {plugin_json}")
            return True

        plugin_md = Path(plugin_path) / ".claude-plugin" / "plugin.md"
        if plugin_md.exists():
            logger.debug(f"Found plugin markdown manifest: {plugin_md}")
            return True

        logger.warning(f"No plugin manifest found in {plugin_path}")
        return False

    async def install_dependencies(self, plugin_path: str) -> bool:
        logger.info(f"Installing dependencies for plugin at: {plugin_path}")

        package_json = Path(plugin_path) / "package.json"
        if not package_json.exists():
            logger.debug(f"No package.json found at {plugin_path}")
            return True

        try:
            logger.info("npm install not implemented - stub")
            return True
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False

    def get_cache_path(self, plugin_id: str, version: str) -> str:
        return os.path.join(self._cache_dir, plugin_id, version)

    def cleanup_cache(self, plugin_id: str, keep_versions: Optional[list] = None) -> None:
        plugin_cache = Path(self._cache_dir) / plugin_id
        if not plugin_cache.exists():
            return

        if keep_versions is None:
            keep_versions = []

        for version_dir in plugin_cache.iterdir():
            if version_dir.is_dir() and version_dir.name not in keep_versions:
                shutil.rmtree(version_dir, ignore_errors=True)
                logger.debug(f"Cleaned up cache version: {version_dir.name}")


async def download_plugin(plugin_id: str, source: str) -> str:
    installer = PluginInstaller()
    return await installer.download_plugin(plugin_id, source)


async def extract_plugin(archive_path: str, dest_dir: str) -> str:
    installer = PluginInstaller()
    return await installer.extract_plugin(archive_path, dest_dir)


def verify_plugin(plugin_path: str) -> bool:
    installer = PluginInstaller()
    return installer.verify_plugin(plugin_path)


async def install_dependencies(plugin_path: str) -> bool:
    installer = PluginInstaller()
    return await installer.install_dependencies(plugin_path)


def compute_checksum(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()