"""Team Memory File Watcher.

Watches the team memory directory for changes and triggers
a debounced push to the server when files are modified.
Performs an initial pull on startup, then starts a directory-level
watch so first-time writes to a fresh repo get picked up.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from .config import get_sync_settings
from .sync import (
    SyncState,
    create_sync_state,
    is_team_memory_sync_available,
    push_team_memory,
    pull_team_memory,
)
from .types import WatcherStatus

logger = logging.getLogger(__name__)

DEBOUNCE_MS = 2000

_watcher: Optional[Any] = None
_debounce_timer: Optional[asyncio.Task] = None
_push_in_progress = False
_has_pending_changes = False
_current_push_task: Optional[asyncio.Task] = None
_watcher_started = False
_push_suppressed_reason: Optional[str] = None
_sync_state: Optional[SyncState] = None


def is_permanent_failure(r: Any) -> bool:
    if r.error_type == "no_oauth" or r.error_type == "no_repo":
        return True
    if r.http_status is not None and 400 <= r.http_status < 500:
        if r.http_status not in (409, 429):
            return True
    return False


async def execute_push() -> None:
    global _push_in_progress, _has_pending_changes, _push_suppressed_reason

    if not _sync_state:
        return

    _push_in_progress = True
    try:
        result = await push_team_memory(_sync_state)
        if result.success:
            _has_pending_changes = False
        if result.success and result.files_uploaded > 0:
            logger.info(f"team-memory-watcher: pushed {result.files_uploaded} files")
        elif not result.success:
            logger.warning(f"team-memory-watcher: push failed: {result.error}")
            if is_permanent_failure(result) and _push_suppressed_reason is None:
                _push_suppressed_reason = (
                    f"http_{result.http_status}" if result.http_status is not None
                    else (result.error_type or "unknown")
                )
                logger.warning(
                    f"team-memory-watcher: suppressing retry until next unlink or session restart ({_push_suppressed_reason})"
                )
    except Exception as e:
        logger.warning(f"team-memory-watcher: push error: {e}")
    finally:
        _push_in_progress = False
        _current_push_task = None


def schedule_push() -> None:
    global _debounce_timer, _has_pending_changes, _push_suppressed_reason

    if _push_suppressed_reason is not None:
        return

    _has_pending_changes = True

    if _debounce_timer:
        _debounce_timer.cancel()

    loop = asyncio.get_event_loop()
    _debounce_timer = loop.call_later(
        DEBOUNCE_MS / 1000,
        lambda: asyncio.create_task(_debounced_push()),
    )


async def _debounced_push() -> None:
    global _debounce_timer
    _debounce_timer = None

    if _push_in_progress:
        schedule_push()
        return

    await execute_push()


async def start_file_watcher(team_dir: str) -> None:
    global _watcher, _watcher_started

    if _watcher_started:
        return

    _watcher_started = True

    try:
        Path(team_dir).mkdir(parents=True, exist_ok=True)

        logger.debug(f"team-memory-watcher: would watch {team_dir}")

    except Exception as e:
        logger.warning(f"team-memory-watcher: failed to watch {team_dir}: {e}")


async def start_team_memory_watcher() -> None:
    global _sync_state, _watcher_started

    settings = get_sync_settings()
    if not settings.sync_enabled:
        return

    if not is_team_memory_sync_available():
        logger.debug("team-memory-watcher: OAuth not available, skipping")
        return

    team_dir = str(Path.home() / ".claude" / "team_memory")

    _sync_state = create_sync_state()

    initial_pull_success = False
    initial_files_pulled = 0
    server_has_content = False

    try:
        pull_result = await pull_team_memory(_sync_state)
        initial_pull_success = pull_result.success
        server_has_content = pull_result.entry_count > 0
        if pull_result.success and pull_result.files_written > 0:
            initial_files_pulled = pull_result.files_written
            logger.info(f"team-memory-watcher: initial pull got {pull_result.files_written} files")
    except Exception as e:
        logger.warning(f"team-memory-watcher: initial pull failed: {e}")

    await start_file_watcher(team_dir)

    logger.info(
        f"team-memory-watcher: started (initial_pull_success={initial_pull_success}, "
        f"initial_files_pulled={initial_files_pulled}, server_has_content={server_has_content})"
    )


async def notify_team_memory_write() -> None:
    if not _sync_state:
        return
    schedule_push()


async def stop_team_memory_watcher() -> None:
    global _debounce_timer, _watcher, _has_pending_changes, _push_suppressed_reason

    if _debounce_timer:
        _debounce_timer.cancel()
        _debounce_timer = None

    _watcher = None

    if _current_push_task:
        try:
            await _current_push_task
        except Exception:
            pass

    if _has_pending_changes and _sync_state and _push_suppressed_reason is None:
        try:
            await push_team_memory(_sync_state)
        except Exception:
            pass


def get_watcher_status() -> WatcherStatus:
    return WatcherStatus(
        is_watching=_watcher_started,
        push_in_progress=_push_in_progress,
        has_pending_changes=_has_pending_changes,
        push_suppressed=_push_suppressed_reason is not None,
        suppress_reason=_push_suppressed_reason,
    )


class TeamMemoryWatcher:
    def __init__(self):
        self._started = False
        self._sync_state: Optional[SyncState] = None

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._sync_state = create_sync_state()
        await start_team_memory_watcher()

    async def stop(self) -> None:
        await stop_team_memory_watcher()
        self._started = False

    def start_watching(self) -> None:
        if self._started:
            return
        asyncio.create_task(self.start())

    def stop_watching(self) -> None:
        asyncio.create_task(self.stop())

    async def on_memory_changed(self, path: str) -> None:
        await notify_team_memory_write()

    def get_status(self) -> WatcherStatus:
        return get_watcher_status()
