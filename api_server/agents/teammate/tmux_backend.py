"""
TmuxBackend implements pane management using tmux for teammate visualization.

When running INSIDE tmux (leader is in tmux):
- Splits the current window to add teammates alongside the leader
- Leader stays on left (30%), teammates on right (70%)

When running OUTSIDE tmux (leader is in regular terminal):
- Creates a claude-swarm session with a swarm-view window
- All teammates are equally distributed (no leader pane)
"""

import asyncio
import os
from typing import TypedDict


# Constants
TMUX_COMMAND = "tmux"
SWARM_SESSION_NAME = "claude-swarm"
SWARM_VIEW_WINDOW_NAME = "swarm-view"
HIDDEN_SESSION_NAME = "claude-hidden"
PANE_SHELL_INIT_DELAY_MS = 200


class AgentColorName(str):
    """Valid agent color names."""
    def __new__(cls, value: str):
        if value not in ('red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'cyan'):
            raise ValueError(f"Invalid color: {value}")
        return super().__new__(cls, value)


class CreatePaneResult(TypedDict):
    """Result of creating a new teammate pane."""
    paneId: str
    isFirstTeammate: bool


# Track whether the first pane has been used for external swarm session
_first_pane_used_for_external = False

# Cached leader window target (session:window format) to avoid repeated queries
_cached_leader_window_target: str | None = None

# Lock mechanism to prevent race conditions when spawning teammates in parallel
_pane_creation_lock: asyncio.Future = asyncio.Future()
_pane_creation_lock.set_result(None)


def _get_swarm_socket_name() -> str:
    """Gets the socket name for external swarm sessions."""
    return f"claude-swarm-{os.getpid()}"


def _get_tmux_color_name(color: AgentColorName) -> str:
    """Gets the tmux color name for a given agent color."""
    tmux_colors: dict[AgentColorName, str] = {
        AgentColorName("red"): "red",
        AgentColorName("blue"): "blue",
        AgentColorName("green"): "green",
        AgentColorName("yellow"): "yellow",
        AgentColorName("purple"): "magenta",
        AgentColorName("orange"): "colour208",
        AgentColorName("pink"): "colour205",
        AgentColorName("cyan"): "cyan",
    }
    return tmux_colors.get(color, "cyan")


async def _run_tmux_in_user_session(args: list[str]) -> tuple[int, str, str]:
    """Runs a tmux command in the user's original tmux session."""
    proc = await asyncio.create_subprocess_exec(
        TMUX_COMMAND,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode("utf-8"), stderr.decode("utf-8")


async def _run_tmux_in_swarm(args: list[str]) -> tuple[int, str, str]:
    """Runs a tmux command in the external swarm socket."""
    proc = await asyncio.create_subprocess_exec(
        TMUX_COMMAND,
        "-L",
        _get_swarm_socket_name(),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode("utf-8"), stderr.decode("utf-8")


def _acquire_pane_creation_lock() -> asyncio.Future:
    """Acquires a lock for pane creation, ensuring sequential execution."""
    global _pane_creation_lock
    current_lock = _pane_creation_lock
    future: asyncio.Future = asyncio.Future()
    _pane_creation_lock = future
    
    async def release_after():
        await current_lock
        if not future.done():
            future.set_result(None)
    
    asyncio.create_task(release_after())
    return current_lock


def _release_lock(lock: asyncio.Future) -> None:
    """Releases the pane creation lock."""
    if not lock.done():
        lock.set_result(None)


async def _sleep(ms: int) -> None:
    """Sleep for the specified milliseconds."""
    await asyncio.sleep(ms / 1000)


class TmuxPaneBackend:
    """
    TmuxBackend implements PaneBackend using tmux for pane management.
    
    This class provides pane management functionality for tmux, including:
    - Creating teammate panes in swarm view
    - Sending commands to panes
    - Setting pane border colors and titles
    - Hiding/showing panes
    - Rebalancing pane layouts
    """
    
    type: str = "tmux"
    display_name: str = "tmux"
    supports_hide_show: bool = True
    
    async def is_available(self) -> bool:
        """Checks if tmux is installed and available."""
        proc = await asyncio.create_subprocess_exec(
            TMUX_COMMAND,
            "-V",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
        return proc.returncode == 0
    
    async def is_running_inside(self) -> bool:
        """Checks if we're currently running inside a tmux session."""
        return bool(os.environ.get("TMUX"))
    
    async def create_teammate_pane_in_swarm_view(
        self,
        name: str,
        color: AgentColorName,
    ) -> CreatePaneResult:
        """Creates a new teammate pane in the swarm view."""
        lock = _acquire_pane_creation_lock()
        try:
            await lock
            
            inside_tmux = await self.is_running_inside()
            
            if inside_tmux:
                return await self._create_teammate_pane_with_leader(name, color)
            
            return await self._create_teammate_pane_external(name, color)
        finally:
            _release_lock(lock)
    
    async def send_command_to_pane(
        self,
        pane_id: str,
        command: str,
        use_external_session: bool = False,
    ) -> None:
        """Sends a command to a specific pane."""
        run_tmux = _run_tmux_in_swarm if use_external_session else _run_tmux_in_user_session
        code, _, stderr = await run_tmux(["send-keys", "-t", pane_id, command, "Enter"])
        
        if code != 0:
            raise RuntimeError(f"Failed to send command to pane {pane_id}: {stderr}")
    
    async def set_pane_border_color(
        self,
        pane_id: str,
        color: AgentColorName,
        use_external_session: bool = False,
    ) -> None:
        """Sets the border color for a specific pane."""
        tmux_color = _get_tmux_color_name(color)
        run_tmux = _run_tmux_in_swarm if use_external_session else _run_tmux_in_user_session
        
        # Set pane-specific border style using pane options
        await run_tmux([
            "select-pane",
            "-t",
            pane_id,
            "-P",
            f"bg=default,fg={tmux_color}",
        ])
        
        await run_tmux([
            "set-option",
            "-p",
            "-t",
            pane_id,
            "pane-border-style",
            f"fg={tmux_color}",
        ])
        
        await run_tmux([
            "set-option",
            "-p",
            "-t",
            pane_id,
            "pane-active-border-style",
            f"fg={tmux_color}",
        ])
    
    async def set_pane_title(
        self,
        pane_id: str,
        name: str,
        color: AgentColorName,
        use_external_session: bool = False,
    ) -> None:
        """Sets the title for a pane."""
        tmux_color = _get_tmux_color_name(color)
        run_tmux = _run_tmux_in_swarm if use_external_session else _run_tmux_in_user_session
        
        # Set the pane title
        await run_tmux(["select-pane", "-t", pane_id, "-T", name])
        
        # Enable pane border status with colored format
        await run_tmux([
            "set-option",
            "-p",
            "-t",
            pane_id,
            "pane-border-format",
            f"#[fg={tmux_color},bold] #{{pane_title}} #[default]",
        ])
    
    async def enable_pane_border_status(
        self,
        window_target: str | None = None,
        use_external_session: bool = False,
    ) -> None:
        """Enables pane border status for a window."""
        target = window_target or await self._get_current_window_target()
        if not target:
            return
        
        run_tmux = _run_tmux_in_swarm if use_external_session else _run_tmux_in_user_session
        await run_tmux([
            "set-option",
            "-w",
            "-t",
            target,
            "pane-border-status",
            "top",
        ])
    
    async def rebalance_panes(
        self,
        window_target: str,
        has_leader: bool,
    ) -> None:
        """Rebalances panes to achieve the desired layout."""
        if has_leader:
            await self._rebalance_panes_with_leader(window_target)
        else:
            await self._rebalance_panes_tiled(window_target)
    
    async def kill_pane(
        self,
        pane_id: str,
        use_external_session: bool = False,
    ) -> bool:
        """Kills/closes a specific pane."""
        run_tmux = _run_tmux_in_swarm if use_external_session else _run_tmux_in_user_session
        code, _, _ = await run_tmux(["kill-pane", "-t", pane_id])
        return code == 0
    
    async def hide_pane(
        self,
        pane_id: str,
        use_external_session: bool = False,
    ) -> bool:
        """Hides a pane by moving it to a detached hidden session."""
        global HIDDEN_SESSION_NAME
        run_tmux = _run_tmux_in_swarm if use_external_session else _run_tmux_in_user_session
        
        # Create hidden session if it doesn't exist
        await run_tmux(["new-session", "-d", "-s", HIDDEN_SESSION_NAME])
        
        # Move the pane to the hidden session
        code, _, stderr = await run_tmux([
            "break-pane",
            "-d",
            "-s",
            pane_id,
            "-t",
            f"{HIDDEN_SESSION_NAME}:",
        ])
        
        return code == 0
    
    async def show_pane(
        self,
        pane_id: str,
        target_window_or_pane: str,
        use_external_session: bool = False,
    ) -> bool:
        """Shows a previously hidden pane by joining it back into the target window."""
        global HIDDEN_SESSION_NAME
        run_tmux = _run_tmux_in_swarm if use_external_session else _run_tmux_in_user_session
        
        # Join the pane back into the target window
        code, _, stderr = await run_tmux([
            "join-pane",
            "-h",
            "-s",
            pane_id,
            "-t",
            target_window_or_pane,
        ])
        
        if code != 0:
            return False
        
        # Reapply main-vertical layout with leader at 30%
        await run_tmux(["select-layout", "-t", target_window_or_pane, "main-vertical"])
        
        # Get the first pane (leader) and resize to 30%
        panes_code, panes_stdout, _ = await run_tmux([
            "list-panes",
            "-t",
            target_window_or_pane,
            "-F",
            "#{pane_id}",
        ])
        
        panes = panes_stdout.strip().split("\n")
        if panes and panes[0]:
            await run_tmux(["resize-pane", "-t", panes[0], "-x", "30%"])
        
        return True
    
    async def create_external_swarm_session(self) -> tuple[str, str]:
        """
        Creates the swarm session with a single window for teammates when running outside tmux.
        
        Returns:
            Tuple of (window_target, pane_id)
        """
        global _first_pane_used_for_external, SWARM_SESSION_NAME, SWARM_VIEW_WINDOW_NAME
        
        # Check if session exists
        code, _, _ = await _run_tmux_in_swarm(["has-session", "-t", SWARM_SESSION_NAME])
        
        window_target = f"{SWARM_SESSION_NAME}:{SWARM_VIEW_WINDOW_NAME}"
        
        if code != 0:
            # Create new session
            code, stdout, stderr = await _run_tmux_in_swarm([
                "new-session",
                "-d",
                "-s",
                SWARM_SESSION_NAME,
                "-n",
                SWARM_VIEW_WINDOW_NAME,
                "-P",
                "-F",
                "#{pane_id}",
            ])
            
            if code != 0:
                raise RuntimeError(f"Failed to create swarm session: {stderr}")
            
            pane_id = stdout.strip()
            return window_target, pane_id
        
        # Session exists, check if swarm-view window exists
        code, windows_out, _ = await _run_tmux_in_swarm([
            "list-windows",
            "-t",
            SWARM_SESSION_NAME,
            "-F",
            "#{window_name}",
        ])
        
        windows = windows_out.strip().split("\n")
        
        if SWARM_VIEW_WINDOW_NAME in windows:
            code, panes_out, _ = await _run_tmux_in_swarm([
                "list-panes",
                "-t",
                window_target,
                "-F",
                "#{pane_id}",
            ])
            
            panes = panes_out.strip().split("\n")
            return window_target, panes[0] if panes else ""
        
        # Create the swarm-view window
        code, pane_out, stderr = await _run_tmux_in_swarm([
            "new-window",
            "-t",
            SWARM_SESSION_NAME,
            "-n",
            SWARM_VIEW_WINDOW_NAME,
            "-P",
            "-F",
            "#{pane_id}",
        ])
        
        if code != 0:
            raise RuntimeError(f"Failed to create swarm-view window: {stderr}")
        
        return window_target, pane_out.strip()
    
    # Private helper methods
    
    async def _get_current_pane_id(self) -> str | None:
        """Gets the leader's pane ID."""
        # Use TMUX_PANE env var if available
        tmux_pane = os.environ.get("TMUX_PANE")
        if tmux_pane:
            return tmux_pane
        
        # Fallback to query
        code, stdout, _ = await _run_tmux_in_user_session([
            "display-message",
            "-p",
            "#{pane_id}",
        ])
        
        if code != 0:
            return None
        
        return stdout.strip()
    
    async def _get_current_window_target(self) -> str | None:
        """Gets the leader's window target (session:window format)."""
        global _cached_leader_window_target
        
        if _cached_leader_window_target:
            return _cached_leader_window_target
        
        leader_pane = await self._get_current_pane_id()
        args = ["display-message"]
        if leader_pane:
            args.extend(["-t", leader_pane])
        args.append("-p")
        args.append("#{session_name}:#{window_index}")
        
        code, stdout, _ = await _run_tmux_in_user_session(args)
        
        if code != 0:
            return None
        
        _cached_leader_window_target = stdout.strip()
        return _cached_leader_window_target
    
    async def _get_current_window_pane_count(
        self,
        window_target: str | None = None,
        use_swarm_socket: bool = False,
    ) -> int | None:
        """Gets the number of panes in a window."""
        target = window_target or await self._get_current_window_target()
        if not target:
            return None
        
        run_tmux = _run_tmux_in_swarm if use_swarm_socket else _run_tmux_in_user_session
        code, stdout, _ = await run_tmux([
            "list-panes",
            "-t",
            target,
            "-F",
            "#{pane_id}",
        ])
        
        if code != 0:
            return None
        
        panes = [p for p in stdout.strip().split("\n") if p]
        return len(panes)
    
    async def _has_session_in_swarm(self, session_name: str) -> bool:
        """Checks if a tmux session exists in the swarm socket."""
        code, _, _ = await _run_tmux_in_swarm(["has-session", "-t", session_name])
        return code == 0
    
    async def _create_teammate_pane_with_leader(
        self,
        teammate_name: str,
        teammate_color: AgentColorName,
    ) -> CreatePaneResult:
        """Creates a teammate pane when running inside tmux (with leader)."""
        global TMUX_COMMAND
        
        current_pane_id = await self._get_current_pane_id()
        window_target = await self._get_current_window_target()
        
        if not current_pane_id or not window_target:
            raise RuntimeError("Could not determine current tmux pane/window")
        
        pane_count = await self._get_current_window_pane_count(window_target)
        if pane_count is None:
            raise RuntimeError("Could not determine pane count for current window")
        
        is_first_teammate = pane_count == 1
        
        if is_first_teammate:
            # First teammate: split horizontally from the leader pane
            code, stdout, stderr = await _run_tmux_in_user_session([
                "split-window",
                "-t",
                current_pane_id,
                "-h",
                "-l",
                "70%",
                "-P",
                "-F",
                "#{pane_id}",
            ])
        else:
            # Additional teammates: split from an existing teammate pane
            code, panes_out, _ = await _run_tmux_in_user_session([
                "list-panes",
                "-t",
                window_target,
                "-F",
                "#{pane_id}",
            ])
            
            panes = [p for p in panes_out.strip().split("\n") if p]
            teammate_panes = panes[1:]  # Skip leader pane
            teammate_count = len(teammate_panes)
            
            split_vertically = teammate_count % 2 == 1
            target_pane_index = (teammate_count - 1) // 2
            target_pane = teammate_panes[target_pane_index] if target_pane_index < len(teammate_panes) else teammate_panes[-1]
            
            code, stdout, stderr = await _run_tmux_in_user_session([
                "split-window",
                "-t",
                target_pane,
                "-v" if split_vertically else "-h",
                "-P",
                "-F",
                "#{pane_id}",
            ])
        
        if code != 0:
            raise RuntimeError(f"Failed to create teammate pane: {stderr}")
        
        pane_id = stdout.strip()
        
        await self.set_pane_border_color(pane_id, teammate_color)
        await self.set_pane_title(pane_id, teammate_name, teammate_color)
        await self._rebalance_panes_with_leader(window_target)
        
        # Wait for shell to initialize
        await _sleep(PANE_SHELL_INIT_DELAY_MS)
        
        return CreatePaneResult(paneId=pane_id, isFirstTeammate=is_first_teammate)
    
    async def _create_teammate_pane_external(
        self,
        teammate_name: str,
        teammate_color: AgentColorName,
    ) -> CreatePaneResult:
        """Creates a teammate pane when running outside tmux (no leader in tmux)."""
        global _first_pane_used_for_external
        
        window_target, first_pane_id = await self.create_external_swarm_session()
        
        pane_count = await self._get_current_window_pane_count(window_target, True)
        if pane_count is None:
            raise RuntimeError("Could not determine pane count for swarm window")
        
        is_first_teammate = not _first_pane_used_for_external and pane_count == 1
        pane_id: str
        
        if is_first_teammate:
            pane_id = first_pane_id
            _first_pane_used_for_external = True
            
            await self.enable_pane_border_status(window_target, True)
        else:
            # Get existing panes and split from one of them
            code, panes_out, _ = await _run_tmux_in_swarm([
                "list-panes",
                "-t",
                window_target,
                "-F",
                "#{pane_id}",
            ])
            
            panes = [p for p in panes_out.strip().split("\n") if p]
            teammate_count = len(panes)
            
            split_vertically = teammate_count % 2 == 1
            target_pane_index = (teammate_count - 1) // 2
            target_pane = panes[target_pane_index] if target_pane_index < len(panes) else panes[-1]
            
            code, stdout, stderr = await _run_tmux_in_swarm([
                "split-window",
                "-t",
                target_pane,
                "-v" if split_vertically else "-h",
                "-P",
                "-F",
                "#{pane_id}",
            ])
            
            if code != 0:
                raise RuntimeError(f"Failed to create teammate pane: {stderr}")
            
            pane_id = stdout.strip()
        
        await self.set_pane_border_color(pane_id, teammate_color, True)
        await self.set_pane_title(pane_id, teammate_name, teammate_color, True)
        await self._rebalance_panes_tiled(window_target)
        
        # Wait for shell to initialize
        await _sleep(PANE_SHELL_INIT_DELAY_MS)
        
        return CreatePaneResult(paneId=pane_id, isFirstTeammate=is_first_teammate)
    
    async def _rebalance_panes_with_leader(self, window_target: str) -> None:
        """Rebalances panes in a window with a leader."""
        code, panes_out, _ = await _run_tmux_in_user_session([
            "list-panes",
            "-t",
            window_target,
            "-F",
            "#{pane_id}",
        ])
        
        panes = [p for p in panes_out.strip().split("\n") if p]
        if len(panes) <= 2:
            return
        
        await _run_tmux_in_user_session([
            "select-layout",
            "-t",
            window_target,
            "main-vertical",
        ])
        
        leader_pane = panes[0]
        await _run_tmux_in_user_session(["resize-pane", "-t", leader_pane, "-x", "30%"])
    
    async def _rebalance_panes_tiled(self, window_target: str) -> None:
        """Rebalances panes in a window without a leader (tiled layout)."""
        code, panes_out, _ = await _run_tmux_in_swarm([
            "list-panes",
            "-t",
            window_target,
            "-F",
            "#{pane_id}",
        ])
        
        panes = [p for p in panes_out.strip().split("\n") if p]
        if len(panes) <= 1:
            return
        
        await _run_tmux_in_swarm(["select-layout", "-t", window_target, "tiled"])


def create_tmux_backend() -> TmuxPaneBackend:
    """Creates a TmuxBackend instance."""
    return TmuxPaneBackend()
