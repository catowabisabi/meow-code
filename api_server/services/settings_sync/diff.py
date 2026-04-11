"""
Settings diff utilities for detecting changes between settings.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from .types import SyncEntry


class SettingsDiffer:
    """Handles diffing of settings to detect changes."""

    @staticmethod
    def diff_settings(
        local: Dict[str, str],
        remote: Dict[str, str],
    ) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
        added: Dict[str, str] = {}
        modified: Dict[str, str] = {}
        removed: Dict[str, str] = {}

        all_keys: Set[str] = set(local.keys()) | set(remote.keys())

        for key in all_keys:
            if key in local and key not in remote:
                removed[key] = local[key]
            elif key not in local and key in remote:
                added[key] = remote[key]
            elif local[key] != remote[key]:
                modified[key] = remote[key]

        return added, modified, removed

    @staticmethod
    def get_changed_keys(
        local: Dict[str, str],
        remote: Dict[str, str],
    ) -> List[str]:
        added, modified, removed = SettingsDiffer.diff_settings(local, remote)
        return list(added.keys()) + list(modified.keys()) + list(removed.keys())

    @staticmethod
    def generate_patch(
        source: Dict[str, str],
        target: Dict[str, str],
    ) -> Dict[str, Optional[str]]:
        patch: Dict[str, Optional[str]] = {}
        all_keys: Set[str] = set(source.keys()) | set(target.keys())

        for key in all_keys:
            if key in source and key not in target:
                patch[key] = None
            elif key not in source and key in target:
                patch[key] = target[key]
            elif source[key] != target[key]:
                patch[key] = target[key]

        return patch

    @staticmethod
    def apply_patch(
        settings: Dict[str, str],
        patch: Dict[str, Optional[str]],
    ) -> Dict[str, str]:
        result = dict(settings)

        for key, value in patch.items():
            if value is None:
                result.pop(key, None)
            else:
                result[key] = value

        return result

    @staticmethod
    def compute_entry_diff(
        local_entries: Dict[str, SyncEntry],
        remote_entries: Dict[str, SyncEntry],
    ) -> Dict[str, Any]:
        added: List[str] = []
        modified: List[str] = []
        removed: List[str] = []
        unchanged: List[str] = []

        all_keys = set(local_entries.keys()) | set(remote_entries.keys())

        for key in all_keys:
            if key not in remote_entries:
                if key in local_entries:
                    removed.append(key)
            elif key not in local_entries:
                added.append(key)
            elif local_entries[key].value != remote_entries[key].value:
                modified.append(key)
            else:
                unchanged.append(key)

        return {
            "added": added,
            "modified": modified,
            "removed": removed,
            "unchanged": unchanged,
        }

    @staticmethod
    def merge_settings(
        base: Dict[str, str],
        local: Dict[str, str],
        remote: Dict[str, str],
    ) -> Dict[str, str]:
        result = dict(base)

        for key, value in remote.items():
            if key not in local:
                result[key] = value

        for key, value in local.items():
            if key not in remote:
                result[key] = value

        for key in set(local.keys()) & set(remote.keys()):
            if local[key] == remote[key]:
                result[key] = local[key]

        return result

    @staticmethod
    def has_changes(
        old: Dict[str, str],
        new: Dict[str, str],
    ) -> bool:
        if set(old.keys()) != set(new.keys()):
            return True
        for key, value in old.items():
            if new.get(key) != value:
                return True
        return False

    @staticmethod
    def get_size_bytes(content: str) -> int:
        return len(content.encode("utf-8"))
