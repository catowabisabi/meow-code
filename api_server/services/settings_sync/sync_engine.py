"""
Settings sync engine - core sync orchestration.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx

from .types import (
    SettingsSyncConfig,
    SettingsSyncFetchResult,
    SettingsSyncUploadResult,
    SyncDirection,
    SyncStatus,
    SyncTrigger,
    UserSyncContent,
    UserSyncData,
)
from .config import (
    get_max_file_size_bytes,
    get_max_retries,
    get_timeout_ms,
    is_auto_sync_enabled,
    is_sync_enabled,
    load_sync_config,
)
from .conflict import ConflictResolver
from .diff import SettingsDiffer
from .storage import SettingsStorage
from .watchdog import SettingsWatchdog


class SettingsSyncEngine:
    def __init__(
        self,
        config: Optional[SettingsSyncConfig] = None,
        storage: Optional[SettingsStorage] = None,
        watchdog: Optional[SettingsWatchdog] = None,
    ):
        self.config = config or load_sync_config()
        self.storage = storage or SettingsStorage()
        self.watchdog = watchdog
        self.conflict_resolver = ConflictResolver(
            default_resolution=self.config.conflict_resolution
        )
        self.differ = SettingsDiffer()
        self._status = SyncStatus.IDLE
        self._last_sync: Optional[float] = None
        self._last_error: Optional[str] = None
        self._sync_callbacks: List[Callable[[SyncStatus, str], None]] = []

    @property
    def status(self) -> SyncStatus:
        return self._status

    @property
    def last_sync(self) -> Optional[float]:
        return self._last_sync

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def add_sync_callback(
        self,
        callback: Callable[[SyncStatus, str], None],
    ) -> None:
        self._sync_callbacks.append(callback)

    def _notify_callbacks(self, status: SyncStatus, message: str) -> None:
        for callback in self._sync_callbacks:
            try:
                callback(status, message)
            except Exception:
                pass

    async def sync(
        self,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        trigger: SyncTrigger = SyncTrigger.MANUAL,
        remote_url: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> bool:
        self._status = SyncStatus.SYNCING
        self._notify_callbacks(self._status, "Starting sync...")

        try:
            if direction == SyncDirection.TO_REMOTE:
                success = await self.sync_to_remote(remote_url, project_id)
            elif direction == SyncDirection.FROM_REMOTE:
                success = await self.sync_from_remote(remote_url, project_id)
            else:
                success = await self.sync_bidirectional(remote_url, project_id)

            if success:
                self._status = SyncStatus.SUCCESS
                self._last_sync = datetime.utcnow().timestamp()
            else:
                self._status = SyncStatus.FAILED

            return success

        except Exception as e:
            self._status = SyncStatus.FAILED
            self._last_error = str(e)
            return False

    async def sync_to_remote(
        self,
        remote_url: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> bool:
        try:
            local_entries = await self._build_entries_from_local(project_id)

            fetch_result = await self._fetch_from_remote(remote_url)
            if not fetch_result.success:
                self._last_error = fetch_result.error or "Fetch failed"
                return False

            remote_entries = {}
            if fetch_result.data and not fetch_result.is_empty:
                remote_entries = fetch_result.data.content.entries

            changed_entries = self._get_changed_entries(local_entries, remote_entries)

            if not changed_entries:
                return True

            upload_result = await self._upload_to_remote(changed_entries, remote_url)
            if upload_result.success:
                self._last_sync = datetime.utcnow().timestamp()
                return True

            self._last_error = upload_result.error or "Upload failed"
            return False

        except Exception as e:
            self._last_error = str(e)
            return False

    async def sync_from_remote(
        self,
        remote_url: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> bool:
        try:
            fetch_result = await self._fetch_from_remote(remote_url)
            if not fetch_result.success:
                self._last_error = fetch_result.error or "Fetch failed"
                return False

            if fetch_result.is_empty:
                return True

            entries = fetch_result.data.content.entries
            await self._apply_remote_entries_to_local(entries, project_id)

            self._last_sync = datetime.utcnow().timestamp()
            return True

        except Exception as e:
            self._last_error = str(e)
            return False

    async def sync_bidirectional(
        self,
        remote_url: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> bool:
        try:
            local_entries = await self._build_entries_from_local(project_id)

            fetch_result = await self._fetch_from_remote(remote_url)
            if not fetch_result.success:
                self._last_error = fetch_result.error or "Fetch failed"
                return False

            remote_entries = {}
            if fetch_result.data and not fetch_result.is_empty:
                remote_entries = fetch_result.data.content.entries

            conflicts = self.conflict_resolver.detect_conflicts(
                local_entries, remote_entries
            )

            if conflicts:
                self._status = SyncStatus.CONFLICT
                self._notify_callbacks(
                    self._status,
                    f"Found {len(conflicts)} conflicts",
                )
                resolved = self.conflict_resolver.apply_resolution(
                    local_entries, conflicts
                )
                local_entries = resolved

            merged = self.differ.merge_settings(
                {}, local_entries, remote_entries
            )

            changed = self._get_changed_entries(merged, remote_entries)
            if changed:
                upload_result = await self._upload_to_remote(changed, remote_url)
                if not upload_result.success:
                    self._last_error = upload_result.error or "Upload failed"
                    return False

            await self._apply_remote_entries_to_local(remote_entries, project_id)

            self._last_sync = datetime.utcnow().timestamp()
            return True

        except Exception as e:
            self._last_error = str(e)
            return False

    async def _fetch_from_remote(
        self,
        remote_url: Optional[str] = None,
        max_retries: Optional[int] = None,
    ) -> SettingsSyncFetchResult:
        if max_retries is None:
            max_retries = get_max_retries()
        timeout_ms = get_timeout_ms()

        if not remote_url:
            remote_url = self._get_default_endpoint()

        headers = await self._get_auth_headers()

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
                    response = await client.get(
                        remote_url,
                        headers=headers,
                    )

                    if response.status_code == 404:
                        return SettingsSyncFetchResult(
                            success=True,
                            is_empty=True,
                        )

                    if response.status_code != 200:
                        return SettingsSyncFetchResult(
                            success=False,
                            error=f"HTTP {response.status_code}",
                        )

                    data = response.json()
                    sync_data = UserSyncData(
                        user_id=data.get("userId", ""),
                        version=data.get("version", 1),
                        last_modified=data.get("lastModified", ""),
                        checksum=data.get("checksum", ""),
                        content=UserSyncContent(
                            entries=data.get("content", {}).get("entries", {})
                        ),
                    )

                    return SettingsSyncFetchResult(
                        success=True,
                        data=sync_data,
                        is_empty=False,
                    )

            except httpx.TimeoutException:
                if attempt >= max_retries:
                    return SettingsSyncFetchResult(
                        success=False,
                        error="Request timeout",
                        skip_retry=True,
                    )
            except httpx.RequestError as e:
                if attempt >= max_retries:
                    return SettingsSyncFetchResult(
                        success=False,
                        error=f"Request error: {str(e)}",
                        skip_retry=True,
                    )

            if attempt < max_retries:
                delay = self._get_retry_delay(attempt)
                await asyncio.sleep(delay / 1000)

        return SettingsSyncFetchResult(
            success=False,
            error="Max retries exceeded",
        )

    async def _upload_to_remote(
        self,
        entries: Dict[str, str],
        remote_url: Optional[str] = None,
    ) -> SettingsSyncUploadResult:
        if not remote_url:
            remote_url = self._get_default_endpoint()

        headers = await self._get_auth_headers()
        headers["Content-Type"] = "application/json"
        timeout_ms = get_timeout_ms()

        try:
            async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
                response = await client.put(
                    remote_url,
                    json={"entries": entries},
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    return SettingsSyncUploadResult(
                        success=True,
                        checksum=data.get("checksum"),
                        last_modified=data.get("lastModified"),
                    )
                else:
                    return SettingsSyncUploadResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                    )

        except Exception as e:
            return SettingsSyncUploadResult(
                success=False,
                error=str(e),
            )

    async def _build_entries_from_local(
        self,
        project_id: Optional[str] = None,
    ) -> Dict[str, str]:
        entries: Dict[str, str] = {}

        user_settings_path = self._get_settings_path("userSettings")
        if user_settings_path and user_settings_path.exists():
            content = await self._try_read_file(user_settings_path)
            if content:
                entries["~/.claude/settings.json"] = content

        user_memory_path = self._get_memory_path("User")
        if user_memory_path and user_memory_path.exists():
            content = await self._try_read_file(user_memory_path)
            if content:
                entries["~/.claude/CLAUDE.md"] = content

        if project_id:
            local_settings_path = self._get_settings_path("localSettings")
            if local_settings_path and local_settings_path.exists():
                content = await self._try_read_file(local_settings_path)
                if content:
                    entries[f"projects/{project_id}/.claude/settings.local.json"] = content

            local_memory_path = self._get_memory_path("Local")
            if local_memory_path and local_memory_path.exists():
                content = await self._try_read_file(local_memory_path)
                if content:
                    entries[f"projects/{project_id}/CLAUDE.local.md"] = content

        return entries

    async def _apply_remote_entries_to_local(
        self,
        entries: Dict[str, str],
        project_id: Optional[str] = None,
    ) -> None:
        for key, content in entries.items():
            if content is None:
                continue

            if key == "~/.claude/settings.json":
                path = self._get_settings_path("userSettings")
                if path:
                    await self._write_file(path, content)
            elif key == "~/.claude/CLAUDE.md":
                path = self._get_memory_path("User")
                if path:
                    await self._write_file(path, content)
            elif project_id and key == f"projects/{project_id}/.claude/settings.local.json":
                path = self._get_settings_path("localSettings")
                if path:
                    await self._write_file(path, content)
            elif project_id and key == f"projects/{project_id}/CLAUDE.local.md":
                path = self._get_memory_path("Local")
                if path:
                    await self._write_file(path, content)

    async def _try_read_file(self, path: Path) -> Optional[str]:
        try:
            if path.exists():
                size = path.stat().st_size
                max_size = get_max_file_size_bytes()
                if size > max_size:
                    return None
                content = path.read_text(encoding="utf-8")
                if content and not content.strip():
                    return None
                return content
            return None
        except Exception:
            return None

    async def _write_file(self, path: Path, content: str) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    def _get_changed_entries(
        self,
        local: Dict[str, str],
        remote: Dict[str, str],
    ) -> Dict[str, str]:
        changed: Dict[str, str] = {}
        for key, value in local.items():
            if remote.get(key) != value:
                changed[key] = value
        return changed

    def _get_default_endpoint(self) -> str:
        return "https://api.claude.ai/api/claude_code/user_settings"

    async def _get_auth_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Claude Code API Server",
        }

    def _get_retry_delay(self, attempt: int) -> int:
        base_delay = 1000
        return min(base_delay * (2 ** attempt), 30000)

    def _get_settings_path(self, source: str) -> Optional[Path]:
        home = Path.home()
        if source == "userSettings":
            return home / ".claude" / "settings.json"
        elif source == "localSettings":
            return Path.cwd() / ".claude" / "settings.local.json"
        return None

    def _get_memory_path(self, memory_type: str) -> Optional[Path]:
        home = Path.home()
        if memory_type == "User":
            return home / ".claude" / "CLAUDE.md"
        elif memory_type == "Local":
            return Path.cwd() / "CLAUDE.local.md"
        return None

    def start_watchdog(
        self,
        paths: List[Path],
        on_change: Optional[Callable[[List[Path]], None]] = None,
    ) -> None:
        if self.watchdog is None:
            self.watchdog = SettingsWatchdog(
                settings_paths=paths,
                on_change_callback=on_change or self._on_settings_changed,
            )
        self.watchdog.start_watching()

    def stop_watchdog(self) -> None:
        if self.watchdog:
            self.watchdog.stop_watching()

    def _on_settings_changed(self, paths: List[Path]) -> None:
        if is_auto_sync_enabled():
            asyncio.create_task(
                self.sync(
                    direction=SyncDirection.TO_REMOTE,
                    trigger=SyncTrigger.AUTOMATIC,
                )
            )

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self._status.value,
            "last_sync": self._last_sync,
            "last_error": self._last_error,
            "enabled": is_sync_enabled(),
        }
