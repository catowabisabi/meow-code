"""Settings merge logic for remote and local settings."""

from typing import Any, Dict, List, Optional, Set

from .types import MergeStrategy, RemotePolicy


class SettingsMerger:
    def __init__(self, strategy: MergeStrategy = MergeStrategy.REMOTE_WINS) -> None:
        self._strategy = strategy
        self._local_overrides: Dict[str, Any] = {}

    def get_merge_strategy(self) -> MergeStrategy:
        return self._strategy

    def set_merge_strategy(self, strategy: MergeStrategy) -> None:
        self._strategy = strategy

    def merge_settings(
        self,
        remote: Dict[str, Any],
        local: Dict[str, Any],
        policy: Optional[RemotePolicy] = None,
    ) -> Dict[str, Any]:
        if self._strategy == MergeStrategy.REMOTE_ONLY:
            return remote.copy() if remote else {}

        if self._strategy == MergeStrategy.LOCAL_ONLY:
            return local.copy() if local else {}

        if self._strategy == MergeStrategy.LOCAL_WINS:
            return self._merge_remote_into_local(remote, local, policy)

        if self._strategy == MergeStrategy.REMOTE_WINS:
            return self._merge_local_into_remote(remote, local, policy)

        return self._smart_merge(remote, local, policy)

    def _merge_remote_into_local(
        self,
        remote: Dict[str, Any],
        local: Dict[str, Any],
        policy: Optional[RemotePolicy],
    ) -> Dict[str, Any]:
        result = local.copy() if local else {}

        for key, value in (remote or {}).items():
            if self._should_apply_remote(key, value, policy):
                if key not in self._local_overrides:
                    result[key] = value

        return result

    def _merge_local_into_remote(
        self,
        remote: Dict[str, Any],
        local: Dict[str, Any],
        policy: Optional[RemotePolicy],
    ) -> Dict[str, Any]:
        result = remote.copy() if remote else {}

        for key, value in (local or {}).items():
            if key in self._local_overrides:
                result[key] = value
            elif policy and key in policy.enforced_keys:
                if key in remote:
                    result[key] = remote[key]
            elif key not in result:
                result[key] = value

        return result

    def _smart_merge(
        self,
        remote: Dict[str, Any],
        local: Dict[str, Any],
        policy: Optional[RemotePolicy],
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        all_keys: Set[str] = set()
        if remote:
            all_keys.update(remote.keys())
        if local:
            all_keys.update(local.keys())

        for key in all_keys:
            if policy and key in policy.blocked_keys:
                continue

            remote_value = remote.get(key) if remote else None
            local_value = local.get(key) if local else None
            is_local_override = key in self._local_overrides

            if is_local_override:
                result[key] = local_value
            elif remote_value is not None:
                if policy and key in policy.enforced_keys:
                    result[key] = remote_value
                elif local_value is None:
                    result[key] = remote_value
                else:
                    result[key] = remote_value
            elif local_value is not None:
                result[key] = local_value

        if policy:
            for key in policy.required_keys:
                if key not in result and key in (policy.default_values or {}):
                    result[key] = policy.default_values[key]

        return result

    def _should_apply_remote(self, key: str, value: Any, policy: Optional[RemotePolicy]) -> bool:
        if policy:
            if key in policy.blocked_keys:
                return False
            if key in policy.enforced_keys:
                return True
        return True

    def resolve_conflicts(
        self,
        remote: Dict[str, Any],
        local: Dict[str, Any],
        policy: Optional[RemotePolicy] = None,
    ) -> Dict[str, Any]:
        return self.merge_settings(remote, local, policy)

    def apply_local_overrides(self, overrides: Dict[str, Any]) -> None:
        self._local_overrides.update(overrides)

    def remove_local_override(self, key: str) -> bool:
        if key in self._local_overrides:
            del self._local_overrides[key]
            return True
        return False

    def get_local_overrides(self) -> Dict[str, Any]:
        return self._local_overrides.copy()

    def clear_local_overrides(self) -> None:
        self._local_overrides.clear()

    def get_conflicts(
        self,
        remote: Dict[str, Any],
        local: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        conflicts = []
        all_keys: Set[str] = set()
        if remote:
            all_keys.update(remote.keys())
        if local:
            all_keys.update(local.keys())

        for key in all_keys:
            remote_value = remote.get(key) if remote else None
            local_value = local.get(key) if local else None

            if remote_value is not None and local_value is not None:
                if remote_value != local_value:
                    conflicts.append({
                        "key": key,
                        "remote_value": remote_value,
                        "local_value": local_value,
                        "resolved_value": self._resolve_single_conflict(key, remote_value, local_value),
                    })

        return conflicts

    def _resolve_single_conflict(self, key: str, remote: Any, local: Any) -> Any:
        if key in self._local_overrides:
            return local
        if self._strategy == MergeStrategy.REMOTE_WINS:
            return remote
        if self._strategy == MergeStrategy.LOCAL_WINS:
            return local
        return remote

    def get_merge_summary(
        self,
        remote: Dict[str, Any],
        local: Dict[str, Any],
        policy: Optional[RemotePolicy] = None,
    ) -> Dict[str, Any]:
        merged = self.merge_settings(remote, local, policy)
        conflicts = self.get_conflicts(remote, local)

        return {
            "strategy": self._strategy.value,
            "total_keys": len(merged),
            "from_remote": sum(1 for k in (remote or {}) if k in merged),
            "from_local": sum(1 for k in (local or {}) if k in merged and (not remote or k not in remote)),
            "overrides_applied": len(self._local_overrides),
            "conflicts_count": len(conflicts),
            "conflicts": conflicts,
        }
