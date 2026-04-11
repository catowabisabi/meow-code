"""
Conflict resolution for settings sync.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

from .types import ConflictResolution, SettingsConflict


class ConflictResolver:
    """Handles detection and resolution of sync conflicts."""

    def __init__(self, default_resolution: ConflictResolution = ConflictResolution.LOCAL_WINS):
        self.default_resolution = default_resolution
        self._pending_conflicts: Dict[str, SettingsConflict] = {}

    def detect_conflicts(
        self,
        local: Dict[str, str],
        remote: Dict[str, str],
        local_modified: Optional[datetime] = None,
        remote_modified: Optional[datetime] = None,
    ) -> List[SettingsConflict]:
        conflicts: List[SettingsConflict] = []
        now = datetime.utcnow()

        all_keys = set(local.keys()) | set(remote.keys())

        for key in all_keys:
            if key in local and key in remote and local[key] != remote[key]:
                conflict = SettingsConflict(
                    key=key,
                    local_value=local[key],
                    remote_value=remote[key],
                    local_modified=local_modified or now,
                    remote_modified=remote_modified or now,
                    resolution=self.default_resolution,
                )
                conflicts.append(conflict)
                self._pending_conflicts[key] = conflict

        return conflicts

    def resolve_conflict(
        self,
        conflict: SettingsConflict,
        resolution: Optional[ConflictResolution] = None,
    ) -> str:
        if resolution is None:
            resolution = conflict.resolution

        if resolution == ConflictResolution.LOCAL_WINS:
            return conflict.local_value
        elif resolution == ConflictResolution.REMOTE_WINS:
            return conflict.remote_value
        elif resolution == ConflictResolution.LOCAL_FIRST:
            return conflict.local_value
        elif resolution == ConflictResolution.REMOTE_FIRST:
            return conflict.remote_value
        elif resolution == ConflictResolution.MERGE:
            return self._merge_values(conflict.local_value, conflict.remote_value)
        else:
            return conflict.local_value

    def get_conflict_resolution(
        self,
        key: str,
        resolution: Optional[ConflictResolution] = None,
    ) -> ConflictResolution:
        if resolution is not None:
            return resolution

        if key in self._pending_conflicts:
            return self._pending_conflicts[key].resolution

        return self.default_resolution

    def apply_resolution(
        self,
        local: Dict[str, str],
        conflicts: List[SettingsConflict],
    ) -> Dict[str, str]:
        result = dict(local)

        for conflict in conflicts:
            resolved_value = self.resolve_conflict(conflict)
            result[conflict.key] = resolved_value

        return result

    def _merge_values(self, local: str, remote: str) -> str:
        if local == remote:
            return local

        try:
            local_json = json.loads(local)
            remote_json = json.loads(remote)
            if isinstance(local_json, dict) and isinstance(remote_json, dict):
                merged = dict(remote_json)
                merged.update(local_json)
                return json.dumps(merged)
        except (json.JSONDecodeError, TypeError):
            pass

        return local

    def get_pending_conflicts(self) -> Dict[str, SettingsConflict]:
        return dict(self._pending_conflicts)

    def clear_pending_conflicts(self) -> None:
        self._pending_conflicts.clear()

    def remove_resolved_conflict(self, key: str) -> None:
        self._pending_conflicts.pop(key, None)

    def has_conflicts(self) -> bool:
        return len(self._pending_conflicts) > 0
