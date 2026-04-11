"""
Settings storage for settings sync service.
"""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .types import SettingsProfile, UserSyncContent, UserSyncData


class SettingsStorage:
    """Handles loading and saving settings to local storage."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path.home() / ".claude" / "settings_sync"
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def get_storage_path(self) -> Path:
        return self.config_dir

    def get_profiles_file(self) -> Path:
        return self.config_dir / "profiles.json"

    def get_settings_file(self) -> Path:
        return self.config_dir / "settings.json"

    def get_backup_dir(self) -> Path:
        backup_dir = self.config_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def load_settings(self) -> Dict[str, Any]:
        path = self.get_settings_file()
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        path = self.get_settings_file()
        try:
            path.write_text(
                json.dumps(settings, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except OSError:
            return False

    def load_profiles(self) -> Dict[str, SettingsProfile]:
        path = self.get_profiles_file()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return {
                    k: SettingsProfile(**v)
                    for k, v in data.get("profiles", {}).items()
                }
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def save_profiles(
        self,
        profiles: Dict[str, SettingsProfile],
        active_profile_id: Optional[str] = None,
        last_sync: Optional[float] = None,
    ) -> bool:
        path = self.get_profiles_file()
        data = {
            "profiles": {k: v.model_dump() for k, v in profiles.items()},
            "active_profile_id": active_profile_id,
            "last_sync": last_sync,
        }
        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except OSError:
            return False

    def backup_settings(self, name: Optional[str] = None) -> Optional[Path]:
        settings_path = self.get_settings_file()
        if not settings_path.exists():
            return None

        if name is None:
            name = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        backup_dir = self.get_backup_dir()
        backup_path = backup_dir / f"settings_{name}.json"

        try:
            shutil.copy2(settings_path, backup_path)
            return backup_path
        except OSError:
            return None

    def get_backup_files(self) -> list[Path]:
        backup_dir = self.get_backup_dir()
        if not backup_dir.exists():
            return []
        return sorted(backup_dir.glob("settings_*.json"), reverse=True)

    def restore_from_backup(self, backup_path: Path) -> bool:
        if not backup_path.exists():
            return False
        settings_path = self.get_settings_file()
        try:
            shutil.copy2(backup_path, settings_path)
            return True
        except OSError:
            return False

    def compute_checksum(self, content: Dict[str, Any]) -> str:
        serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()

    def load_user_sync_data(self) -> Optional[UserSyncData]:
        path = self.get_settings_file()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if "user_id" in data:
                    return UserSyncData(
                        user_id=data["user_id"],
                        version=data.get("version", 1),
                        last_modified=data.get("last_modified", ""),
                        checksum=data.get("checksum", ""),
                        content=UserSyncContent(
                            entries=data.get("content", {}).get("entries", {})
                        ),
                    )
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def save_user_sync_data(self, sync_data: UserSyncData) -> bool:
        path = self.get_settings_file()
        data = {
            "user_id": sync_data.user_id,
            "version": sync_data.version,
            "last_modified": sync_data.last_modified,
            "checksum": sync_data.checksum,
            "content": {"entries": sync_data.content.entries},
        }
        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except OSError:
            return False
