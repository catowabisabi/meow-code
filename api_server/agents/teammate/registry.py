"""
Registry for teammate backend detection and selection.

Detection priority:
1. If inside tmux, always use tmux (even in iTerm2)
2. If in iTerm2 with it2 available, use iTerm2 backend
3. If in iTerm2 without it2, return result indicating setup needed
4. If tmux available, use tmux (creates external session)
5. Otherwise, return in-process backend
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import TypedDict

from .executor import BackendType, TeammateExecutor
from .pane_executor import PaneBackendExecutor
from .tmux_backend import create_tmux_backend
from .iterm_backend import create_iterm_backend


TMUX_COMMAND = "tmux"
IT2_COMMAND = "it2"


class BackendDetectionResult(TypedDict):
    """Result from backend detection."""
    backend: "PaneBackend"
    is_native: bool
    needs_it2_setup: bool


# Cached backend detection result
_cached_backend: "PaneBackend | None" = None
_cached_detection_result: BackendDetectionResult | None = None


def _is_inside_tmux_sync() -> bool:
    """Checks if we're currently running inside a tmux session (synchronous)."""
    return bool(os.environ.get("TMUX"))


async def _is_inside_tmux() -> bool:
    """Checks if we're currently running inside a tmux session."""
    return _is_inside_tmux_sync()


async def _is_tmux_available() -> bool:
    """Checks if tmux is available on the system."""
    proc = await asyncio.create_subprocess_exec(
        TMUX_COMMAND,
        "-V",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.wait()
    return proc.returncode == 0


def _is_in_iterm2() -> bool:
    """Checks if we're currently running inside iTerm2."""
    term_program = os.environ.get("TERM_PROGRAM")
    has_iterm_session_id = bool(os.environ.get("ITERM_SESSION_ID"))
    return term_program == "iTerm.app" or has_iterm_session_id


async def _is_it2_cli_available() -> bool:
    """Checks if the it2 CLI tool is available."""
    proc = await asyncio.create_subprocess_exec(
        IT2_COMMAND,
        "session",
        "list",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.wait()
    return proc.returncode == 0


class PaneBackend:
    """Interface for pane-based backends."""
    
    type: BackendType
    display_name: str
    supports_hide_show: bool
    
    async def is_available(self) -> bool:
        raise NotImplementedError
    
    async def is_running_inside(self) -> bool:
        raise NotImplementedError
    
    async def create_teammate_pane_in_swarm_view(
        self,
        name: str,
        color: str,
    ) -> dict:
        raise NotImplementedError
    
    async def send_command_to_pane(
        self,
        pane_id: str,
        command: str,
        use_external_session: bool = False,
    ) -> None:
        raise NotImplementedError
    
    async def set_pane_border_color(
        self,
        pane_id: str,
        color: str,
        use_external_session: bool = False,
    ) -> None:
        raise NotImplementedError
    
    async def set_pane_title(
        self,
        pane_id: str,
        name: str,
        color: str,
        use_external_session: bool = False,
    ) -> None:
        raise NotImplementedError
    
    async def enable_pane_border_status(
        self,
        window_target: str | None = None,
        use_external_session: bool = False,
    ) -> None:
        raise NotImplementedError
    
    async def rebalance_panes(
        self,
        window_target: str,
        has_leader: bool,
    ) -> None:
        raise NotImplementedError
    
    async def kill_pane(
        self,
        pane_id: str,
        use_external_session: bool = False,
    ) -> bool:
        raise NotImplementedError
    
    async def hide_pane(
        self,
        pane_id: str,
        use_external_session: bool = False,
    ) -> bool:
        raise NotImplementedError
    
    async def show_pane(
        self,
        pane_id: str,
        target_window_or_pane: str,
        use_external_session: bool = False,
    ) -> bool:
        raise NotImplementedError


def _get_platform() -> str:
    """Gets the current platform."""
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform == "linux":
        return "linux"
    elif sys.platform == "win32":
        return "windows"
    return "unknown"


def _get_tmux_install_instructions() -> str:
    """Returns platform-specific tmux installation instructions."""
    platform = _get_platform()
    
    if platform == "macos":
        return (
            "To use agent swarms, install tmux:\n"
            "  brew install tmux\n"
            "Then start a tmux session with: tmux new-session -s claude"
        )
    elif platform in ("linux", "wsl"):
        return (
            "To use agent swarms, install tmux:\n"
            "  sudo apt install tmux    # Ubuntu/Debian\n"
            "  sudo dnf install tmux    # Fedora/RHEL\n"
            "Then start a tmux session with: tmux new-session -s claude"
        )
    elif platform == "windows":
        return (
            "To use agent swarms, you need tmux which requires WSL (Windows Subsystem for Linux).\n"
            "Install WSL first, then inside WSL run:\n"
            "  sudo apt install tmux\n"
            "Then start a tmux session with: tmux new-session -s claude"
        )
    else:
        return (
            "To use agent swarms, install tmux using your system's package manager.\n"
            "Then start a tmux session with: tmux new-session -s claude"
        )


async def detect_and_get_backend() -> BackendDetectionResult:
    """
    Detects and returns the appropriate pane backend.
    
    Detection priority:
    1. If inside tmux, always use tmux (even in iTerm2)
    2. If in iTerm2 with it2 available, use iTerm2 backend
    3. If in iTerm2 without it2, fall back to tmux if available
    4. If tmux available, use tmux (external session)
    5. Otherwise, raise error
    """
    global _cached_backend, _cached_detection_result
    
    if _cached_detection_result:
        return _cached_detection_result
    
    inside_tmux = await _is_inside_tmux()
    in_iterm2 = _is_in_iterm2()
    
    if inside_tmux:
        backend = create_tmux_backend()
        _cached_backend = backend
        _cached_detection_result = BackendDetectionResult(
            backend=backend,
            is_native=True,
            needs_it2_setup=False,
        )
        return _cached_detection_result
    
    if in_iterm2:
        it2_available = await _is_it2_cli_available()
        
        if it2_available:
            backend = create_iterm_backend()
            _cached_backend = backend
            _cached_detection_result = BackendDetectionResult(
                backend=backend,
                is_native=True,
                needs_it2_setup=False,
            )
            return _cached_detection_result
        
        tmux_available = await _is_tmux_available()
        
        if tmux_available:
            backend = create_tmux_backend()
            _cached_backend = backend
            _cached_detection_result = BackendDetectionResult(
                backend=backend,
                is_native=False,
                needs_it2_setup=True,
            )
            return _cached_detection_result
        
        raise RuntimeError(
            "iTerm2 detected but it2 CLI not installed. Install it2 with: pip install it2"
        )
    
    tmux_available = await _is_tmux_available()
    
    if tmux_available:
        backend = create_tmux_backend()
        _cached_backend = backend
        _cached_detection_result = BackendDetectionResult(
            backend=backend,
            is_native=False,
            needs_it2_setup=False,
        )
        return _cached_detection_result
    
    raise RuntimeError(_get_tmux_install_instructions())


def get_backend_by_type(backend_type: str) -> PaneBackend:
    """Gets a backend by explicit type selection."""
    if backend_type == "tmux":
        return create_tmux_backend()
    elif backend_type == "iterm2":
        return create_iterm_backend()
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")


def get_cached_backend() -> PaneBackend | None:
    """Gets the currently cached backend."""
    return _cached_backend


def get_cached_detection_result() -> BackendDetectionResult | None:
    """Gets the cached backend detection result."""
    return _cached_detection_result


def reset_backend_detection() -> None:
    """Resets the backend detection cache."""
    global _cached_backend, _cached_detection_result
    _cached_backend = None
    _cached_detection_result = None


async def get_teammate_executor(
    prefer_in_process: bool = False,
    storage_dir: Path | None = None,
) -> TeammateExecutor:
    """
    Gets a TeammateExecutor for spawning teammates.
    
    Args:
        prefer_in_process: If True and in-process is enabled, returns InProcessBackend.
        storage_dir: Optional storage directory for mailbox files.
    
    Returns:
        TeammateExecutor instance
    """
    from .backends import get_executor
    
    if prefer_in_process:
        return get_executor(BackendType.IN_PROCESS, storage_dir)
    
    detection = await detect_and_get_backend()
    return PaneBackendExecutor(detection.backend, storage_dir)


# Public detection functions
async def is_tmux_available() -> bool:
    """Checks if tmux is available."""
    return await _is_tmux_available()


async def is_inside_tmux() -> bool:
    """Checks if we're currently running inside a tmux session."""
    return await _is_inside_tmux()


def is_iterm_available() -> bool:
    """Checks if iTerm2 is available."""
    return _is_in_iterm2()
