"""
Settings watchdog for monitoring and responding to file changes.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from watchfiles import watch


class SettingsWatchdog:
    """Monitors settings files for changes and triggers sync."""

    def __init__(
        self,
        settings_paths: Optional[List[Path]] = None,
        debounce_ms: int = 500,
        on_change_callback: Optional[Callable[[List[Path]], None]] = None,
    ):
        self.settings_paths = settings_paths or []
        self.debounce_ms = debounce_ms
        self.on_change_callback = on_change_callback
        self._watch_task: Optional[asyncio.Task] = None
        self._running = False
        self._debounce_timer: Optional[asyncio.Task] = None
        self._pending_changes: Set[Path] = set()
        self._last_change_time: Dict[Path, datetime] = {}

    def start_watching(self) -> None:
        if self._running:
            return
        self._running = True
        self._watch_task = asyncio.create_task(self._watch_loop())

    def stop_watching(self) -> None:
        self._running = False
        if self._watch_task:
            self._watch_task.cancel()
            self._watch_task = None
        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None

    async def _watch_loop(self) -> None:
        while self._running:
            try:
                async for changes in watch(
                    *self.settings_paths,
                    watch_filter=None,
                    debounce_ms=self.debounce_ms,
                ):
                    await self._handle_changes(changes)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _handle_changes(self, changes: Set[Any]) -> None:
        for change in changes:
            path = Path(change) if not isinstance(change, Path) else change
            self._pending_changes.add(path)
            self._last_change_time[path] = datetime.utcnow()

        if self._debounce_timer:
            self._debounce_timer.cancel()

        self._debounce_timer = asyncio.create_task(self._debounce_and_notify())

    async def _debounce_and_notify(self) -> None:
        await asyncio.sleep(self.debounce_ms / 1000.0)
        if self._pending_changes and self.on_change_callback:
            paths = list(self._pending_changes)
            self._pending_changes.clear()
            self.on_change_callback(paths)

    def on_settings_changed(
        self,
        paths: List[Path],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self.on_change_callback:
            self.on_change_callback(paths)

    def debounce_changes(
        self,
        paths: List[Path],
        delay_ms: Optional[int] = None,
    ) -> None:
        delay = delay_ms or self.debounce_ms
        for path in paths:
            self._pending_changes.add(path)

        if self._debounce_timer:
            self._debounce_timer.cancel()

        async def delayed_notify():
            await asyncio.sleep(delay / 1000.0)
            if self._pending_changes and self.on_change_callback:
                self.on_change_callback(list(self._pending_changes))
                self._pending_changes.clear()

        self._debounce_timer = asyncio.create_task(delayed_notify())

    def add_watched_path(self, path: Path) -> None:
        if path not in self.settings_paths:
            self.settings_paths.append(path)

    def remove_watched_path(self, path: Path) -> None:
        if path in self.settings_paths:
            self.settings_paths.remove(path)

    def is_running(self) -> bool:
        return self._running

    def get_pending_changes(self) -> Set[Path]:
        return set(self._pending_changes)

    def clear_pending_changes(self) -> None:
        self._pending_changes.clear()
