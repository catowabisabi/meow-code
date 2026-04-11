"""Remote settings client for fetching, pushing, and syncing settings."""

import hashlib
import json
from typing import Any, Dict, Optional

from .cache import SettingsCache
from .config import get_remote_url, get_timeout_ms
from .merge import SettingsMerger
from .policy import RemotePolicyManager
from .types import (
    EligibilityStatus,
    RemoteManagedSettingsFetchResult,
    RemotePolicy,
    SettingsSyncStatus,
)
from .watchdog import SettingsWatchdog


class RemoteSettingsClient:
    _instance: Optional["RemoteSettingsClient"] = None
    _eligibility_cache: Optional[bool] = None

    def __new__(cls) -> "RemoteSettingsClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._cache = SettingsCache.get_instance()
        self._merger = SettingsMerger()
        self._policy_manager = RemotePolicyManager()
        self._watchdog = SettingsWatchdog.get_instance()
        self._eligibility: Optional[EligibilityStatus] = None

    @classmethod
    def get_instance(cls) -> "RemoteSettingsClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def fetch_settings(self, url: Optional[str] = None) -> RemoteManagedSettingsFetchResult:
        target_url = url or get_remote_url()
        if not target_url:
            return RemoteManagedSettingsFetchResult(
                success=False,
                error="No remote URL configured",
                skip_retry=True,
            )

        try:
            cached = self._cache.get_all_cached_settings()
            cached_checksum = self._get_checksum(cached) if cached else None

            import urllib.request
            headers: Dict[str, str] = {
                "User-Agent": "ClaudeCode/RemoteSettings",
            }

            if cached_checksum and self._cache.has_valid_cache():
                headers["If-None-Match"] = f'"{cached_checksum}"'

            req = urllib.request.Request(target_url, headers=headers)
            with urllib.request.urlopen(req, timeout=get_timeout_ms() / 1000) as response:
                status = response.status

                if status == 304:
                    return RemoteManagedSettingsFetchResult(
                        success=True,
                        settings=None,
                        checksum=cached_checksum,
                    )

                if status == 204 or status == 404:
                    return RemoteManagedSettingsFetchResult(
                        success=True,
                        settings={},
                        checksum=None,
                    )

                data = json.loads(response.read().decode("utf-8"))

                if not isinstance(data, dict):
                    return RemoteManagedSettingsFetchResult(
                        success=False,
                        error="Invalid response format",
                    )

                settings = data.get("settings", {})
                checksum = data.get("checksum", "")

                self._cache.invalidate_cache()
                for key, value in settings.items():
                    self._cache.set_cached_settings(key, value, checksum)

                self._cache.save_to_file(settings, checksum)

                return RemoteManagedSettingsFetchResult(
                    success=True,
                    settings=settings,
                    checksum=checksum,
                )

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return RemoteManagedSettingsFetchResult(
                    success=True,
                    settings={},
                    checksum=None,
                )
            if e.code in (401, 403):
                return RemoteManagedSettingsFetchResult(
                    success=False,
                    error=f"Not authorized: {e.code}",
                    skip_retry=True,
                )
            return RemoteManagedSettingsFetchResult(
                success=False,
                error=f"HTTP error: {e.code}",
            )
        except Exception as e:
            return RemoteManagedSettingsFetchResult(
                success=False,
                error=str(e),
            )

    async def fetch_settings_async(self, url: Optional[str] = None) -> RemoteManagedSettingsFetchResult:
        import asyncio

        def _fetch() -> RemoteManagedSettingsFetchResult:
            return self.fetch_settings(url)

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    def push_settings(
        self,
        settings: Dict[str, Any],
        url: Optional[str] = None,
    ) -> bool:
        target_url = url or get_remote_url()
        if not target_url:
            return False

        try:
            import urllib.request

            data = json.dumps({"settings": settings}).encode("utf-8")
            req = urllib.request.Request(
                target_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ClaudeCode/RemoteSettings",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=get_timeout_ms() / 1000) as response:
                return response.status in (200, 201, 204)

        except Exception:
            return False

    async def push_settings_async(
        self,
        settings: Dict[str, Any],
        url: Optional[str] = None,
    ) -> bool:
        import asyncio

        def _push() -> bool:
            return self.push_settings(settings, url)

        return await asyncio.get_event_loop().run_in_executor(None, _push)

    def sync_settings(
        self,
        local: Optional[Dict[str, Any]] = None,
        policy: Optional[RemotePolicy] = None,
    ) -> Dict[str, Any]:
        result = self.fetch_settings()

        if not result.success:
            cached = self._cache.get_all_cached_settings()
            if cached:
                return self._merger.merge_settings(cached, local or {}, policy)
            return local or {}

        if result.settings is None:
            cached = self._cache.get_all_cached_settings()
            return self._merger.merge_settings(cached or {}, local or {}, policy)

        if policy:
            self._policy_manager.set_current_policy(policy)

        return self._merger.merge_settings(result.settings or {}, local or {}, policy)

    async def sync_settings_async(
        self,
        local: Optional[Dict[str, Any]] = None,
        policy: Optional[RemotePolicy] = None,
    ) -> Dict[str, Any]:
        import asyncio

        def _sync() -> Dict[str, Any]:
            return self.sync_settings(local, policy)

        return await asyncio.get_event_loop().run_in_executor(None, _sync)

    def get_settings_version(self) -> Optional[str]:
        all_cached = self._cache.get_all_cached_settings()
        if not all_cached:
            return None
        return self._get_checksum(all_cached)

    def _get_checksum(self, settings: Dict[str, Any]) -> str:
        sorted_settings = self._sort_keys_deep(settings)
        normalized = json.dumps(sorted_settings, separators=(",", ":"))
        hash_value = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"sha256:{hash_value}"

    def _sort_keys_deep(self, obj: Any) -> Any:
        if isinstance(obj, list):
            return [self._sort_keys_deep(item) for item in obj]
        if isinstance(obj, dict):
            return {key: self._sort_keys_deep(value) for key, value in sorted(obj.items())}
        return obj

    def get_cached_settings(self) -> Dict[str, Any]:
        return self._cache.get_all_cached_settings()

    def invalidate_cache(self, key: Optional[str] = None) -> None:
        self._cache.invalidate_cache(key)

    def set_local_override(self, key: str, value: Any) -> None:
        self._merger.apply_local_overrides({key: value})

    def remove_local_override(self, key: str) -> bool:
        return self._merger.remove_local_override(key)

    def get_local_overrides(self) -> Dict[str, Any]:
        return self._merger.get_local_overrides()

    def clear_local_overrides(self) -> None:
        self._merger.clear_local_overrides()

    def is_eligible(self) -> EligibilityStatus:
        if self._eligibility is not None:
            return self._eligibility

        import os

        provider = os.environ.get("CLAUDE_API_PROVIDER", "firstParty")
        if provider != "firstParty":
            self._eligibility = EligibilityStatus(
                eligible=False,
                reason="Third-party provider users are not eligible",
                provider=provider,
            )
            return self._eligibility

        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
        if base_url and "anthropic" not in base_url.lower():
            self._eligibility = EligibilityStatus(
                eligible=False,
                reason="Custom base URL users are not eligible",
                provider=provider,
            )
            return self._eligibility

        self._eligibility = EligibilityStatus(
            eligible=True,
            reason="Eligible for remote managed settings",
            provider=provider,
        )
        return self._eligibility

    def get_sync_status(self) -> SettingsSyncStatus:
        if self._cache.has_valid_cache():
            return SettingsSyncStatus.SYNCED
        return SettingsSyncStatus.PENDING

    def reset_eligibility(self) -> None:
        self._eligibility = None
