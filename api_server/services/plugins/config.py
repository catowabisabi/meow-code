import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SETTINGS_FILE = ".claude/settings.json"
CLAUDE_MD_FILE = "CLAUDE.md"


def load_plugin_config(project_path: Optional[str] = None) -> dict:
    logger.info("Loading plugin configuration")

    config = {
        "enabled_plugins": {},
        "plugin_configs": {},
    }

    settings = _load_settings_file(project_path)
    if settings:
        config["enabled_plugins"] = settings.get("enabledPlugins", {})
        config["plugin_configs"] = settings.get("pluginConfigs", {})

    claude_md = _load_claude_md(project_path)
    if claude_md:
        config["from_claude_md"] = claude_md

    return config


def _load_settings_file(project_path: Optional[str] = None) -> Optional[dict]:
    if project_path is None:
        project_path = os.getcwd()

    settings_path = Path(project_path) / SETTINGS_FILE

    if not settings_path.exists():
        logger.debug(f"Settings file not found: {settings_path}")
        return None

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load settings file: {e}")
        return None


def _load_claude_md(project_path: Optional[str] = None) -> Optional[dict]:
    if project_path is None:
        project_path = os.getcwd()

    claude_md_path = Path(project_path) / CLAUDE_MD_FILE

    if not claude_md_path.exists():
        logger.debug(f"CLAUDE.md not found: {claude_md_path}")
        return None

    try:
        content = claude_md_path.read_text(encoding="utf-8")
        return _parse_claude_md(content)
    except Exception as e:
        logger.error(f"Failed to load CLAUDE.md: {e}")
        return None


def _parse_claude_md(content: str) -> dict:
    result = {
        "plugins": [],
        "marketplaces": [],
    }

    current_section = None
    for line in content.split("\n"):
        line = line.strip()

        if line.startswith("## ") and "plugin" in line.lower():
            current_section = "plugins"
            continue

        if line.startswith("### ") and "marketplace" in line.lower():
            current_section = "marketplaces"
            continue

        if line.startswith("- ") and current_section == "plugins":
            plugin_name = line[2:].strip()
            if plugin_name:
                result["plugins"].append(plugin_name)

        if line.startswith("- ") and current_section == "marketplaces":
            marketplace = line[2:].strip()
            if marketplace:
                result["marketplaces"].append(marketplace)

    return result


def get_enabled_plugins(project_path: Optional[str] = None) -> list[str]:
    config = load_plugin_config(project_path)
    enabled = config.get("enabled_plugins", {})

    return [pid for pid, val in enabled.items() if val is True]


def get_plugin_settings(
    plugin_id: str,
    project_path: Optional[str] = None,
) -> Optional[dict]:
    config = load_plugin_config(project_path)
    plugin_configs = config.get("plugin_configs", {})

    return plugin_configs.get(plugin_id)


def update_plugin_settings(
    plugin_id: str,
    settings: dict,
    project_path: Optional[str] = None,
) -> bool:
    if project_path is None:
        project_path = os.getcwd()

    settings_path = Path(project_path) / SETTINGS_FILE

    current_settings = _load_settings_file(project_path) or {}

    if "pluginConfigs" not in current_settings:
        current_settings["pluginConfigs"] = {}

    current_settings["pluginConfigs"][plugin_id] = settings

    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(current_settings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to update plugin settings: {e}")
        return False


def set_plugin_enabled(
    plugin_id: str,
    enabled: bool,
    scope: str = "user",
    project_path: Optional[str] = None,
) -> bool:
    if project_path is None:
        project_path = os.getcwd()

    settings_path = Path(project_path) / SETTINGS_FILE
    current_settings = _load_settings_file(project_path) or {}

    if "enabledPlugins" not in current_settings:
        current_settings["enabledPlugins"] = {}

    current_settings["enabledPlugins"][plugin_id] = enabled

    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(current_settings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to set plugin enabled: {e}")
        return False


def get_all_plugin_configs(project_path: Optional[str] = None) -> dict:
    config = load_plugin_config(project_path)
    return config.get("plugin_configs", {})


def delete_plugin_config(
    plugin_id: str,
    project_path: Optional[str] = None,
) -> bool:
    if project_path is None:
        project_path = os.getcwd()

    settings_path = Path(project_path) / SETTINGS_FILE
    current_settings = _load_settings_file(project_path) or {}

    if "pluginConfigs" in current_settings and plugin_id in current_settings["pluginConfigs"]:
        del current_settings["pluginConfigs"][plugin_id]

        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(current_settings, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to delete plugin config: {e}")
            return False

    return True