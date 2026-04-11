"""
ITermBackend implements pane management using iTerm2's native split panes via the it2 CLI.

iTerm2 backend provides:
- Split pane creation using it2 session split
- Dead session recovery via it2 session list
- No border color support (not supported by iTerm2)
"""

import asyncio
import os
from typing import TypedDict

from .tmux_backend import AgentColorName


IT2_COMMAND = "it2"

# Track session IDs for teammates
teammate_session_ids: list[str] = []

# Track whether the first pane has been used
first_pane_used = False

# Lock mechanism to prevent race conditions when spawning teammates in parallel
_pane_creation_lock: asyncio.Future = asyncio.Future()
_pane_creation_lock.set_result(None)


class CreatePaneResult(TypedDict):
    """Result of creating a new teammate pane."""
    paneId: str
    isFirstTeammate: bool


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


async def _run_it2(args: list[str]) -> tuple[int, str, str]:
    """Runs an it2 CLI command and returns the result."""
    proc = await asyncio.create_subprocess_exec(
        IT2_COMMAND,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode("utf-8"), stderr.decode("utf-8")


def _parse_split_output(output: str) -> str:
    """Parses the session ID from `it2 session split` output."""
    import re
    match = re.search(r"Created new pane:\s*(.+)", output)
    if match and match.group(1):
        return match.group(1).strip()
    return ""


def _get_leader_session_id() -> str | None:
    """Gets the leader's session ID from ITERM_SESSION_ID env var."""
    iterm_session_id = os.environ.get("ITERM_SESSION_ID")
    if not iterm_session_id:
        return None
    colon_index = iterm_session_id.index(":")
    if colon_index == -1:
        return None
    return iterm_session_id[colon_index + 1:]


def _is_in_iterm2() -> bool:
    """Checks if we're currently running inside iTerm2."""
    term_program = os.environ.get("TERM_PROGRAM")
    has_iterm_session_id = bool(os.environ.get("ITERM_SESSION_ID"))
    return term_program == "iTerm.app" or has_iterm_session_id


async def _is_it2_cli_available() -> bool:
    """Checks if the it2 CLI tool is available and can reach the iTerm2 Python API."""
    code, _, _ = await _run_it2(["session", "list"])
    return code == 0


class ITermPaneBackend:
    """
    ITermBackend implements pane management using iTerm2's native split panes via the it2 CLI.
    
    Features:
    - Split pane creation via it2 session split
    - Dead session recovery via it2 session list
    - No border color support (not supported by iTerm2)
    - No hide/show support (no equivalent to tmux's break-pane/join-pane)
    """
    
    type: str = "iterm2"
    display_name: str = "iTerm2"
    supports_hide_show: bool = False
    
    async def is_available(self) -> bool:
        """Checks if iTerm2 backend is available (in iTerm2 with it2 CLI installed)."""
        if not _is_in_iterm2():
            return False
        return await _is_it2_cli_available()
    
    async def is_running_inside(self) -> bool:
        """Checks if we're currently running inside iTerm2."""
        return _is_in_iterm2()
    
    async def create_teammate_pane_in_swarm_view(
        self,
        name: str,
        color: AgentColorName,
    ) -> CreatePaneResult:
        """Creates a new teammate pane in the swarm view."""
        global first_pane_used, teammate_session_ids
        
        lock = _acquire_pane_creation_lock()
        try:
            await lock
            
            while True:
                is_first_teammate = not first_pane_used
                
                split_args: list[str]
                targeted_teammate_id: str | None = None
                
                if is_first_teammate:
                    leader_session_id = _get_leader_session_id()
                    if leader_session_id:
                        split_args = ["session", "split", "-v", "-s", leader_session_id]
                    else:
                        split_args = ["session", "split", "-v"]
                else:
                    targeted_teammate_id = teammate_session_ids[-1] if teammate_session_ids else None
                    if targeted_teammate_id:
                        split_args = ["session", "split", "-s", targeted_teammate_id]
                    else:
                        split_args = ["session", "split"]
                
                split_result = await _run_it2(split_args)
                
                if split_result[0] != 0:
                    if targeted_teammate_id:
                        list_result = await _run_it2(["session", "list"])
                        if list_result[0] == 0 and targeted_teammate_id not in list_result[1]:
                            idx = teammate_session_ids.index(targeted_teammate_id)
                            if idx != -1:
                                teammate_session_ids.pop(idx)
                            if len(teammate_session_ids) == 0:
                                first_pane_used = False
                            continue
                    raise RuntimeError(f"Failed to create iTerm2 split pane: {split_result[2]}")
                
                if is_first_teammate:
                    first_pane_used = True
                
                pane_id = _parse_split_output(split_result[1])
                
                if not pane_id:
                    raise RuntimeError(f"Failed to parse session ID from split output: {split_result[1]}")
                
                teammate_session_ids.append(pane_id)
                
                return CreatePaneResult(paneId=pane_id, isFirstTeammate=is_first_teammate)
        finally:
            _release_lock(lock)
    
    async def send_command_to_pane(
        self,
        pane_id: str,
        command: str,
        _use_external_session: bool = False,
    ) -> None:
        """Sends a command to a specific pane."""
        args = ["session", "run", "-s", pane_id, command] if pane_id else ["session", "run", command]
        
        result = await _run_it2(args)
        
        if result[0] != 0:
            raise RuntimeError(f"Failed to send command to iTerm2 pane {pane_id}: {result[2]}")
    
    async def set_pane_border_color(
        self,
        _pane_id: str,
        _color: AgentColorName,
        _use_external_session: bool = False,
    ) -> None:
        """No-op for iTerm2 - not supported."""
        pass
    
    async def set_pane_title(
        self,
        _pane_id: str,
        _name: str,
        _color: AgentColorName,
        _use_external_session: bool = False,
    ) -> None:
        """No-op for iTerm2 - not supported."""
        pass
    
    async def enable_pane_border_status(
        self,
        _window_target: str | None = None,
        _use_external_session: bool = False,
    ) -> None:
        """No-op for iTerm2 - titles are shown in tabs automatically."""
        pass
    
    async def rebalance_panes(
        self,
        _window_target: str,
        _has_leader: bool,
    ) -> None:
        """No-op for iTerm2 - pane balancing is handled automatically."""
        pass
    
    async def kill_pane(
        self,
        pane_id: str,
        _use_external_session: bool = False,
    ) -> bool:
        """Kills/closes a specific pane using the it2 CLI."""
        global teammate_session_ids, first_pane_used
        
        result = await _run_it2(["session", "close", "-f", "-s", pane_id])
        
        idx = pane_id in teammate_session_ids and teammate_session_ids.index(pane_id)
        if idx != -1:
            teammate_session_ids.pop(idx)
        
        if len(teammate_session_ids) == 0:
            first_pane_used = False
        
        return result[0] == 0
    
    async def hide_pane(
        self,
        _pane_id: str,
        _use_external_session: bool = False,
    ) -> bool:
        """Stub for hiding a pane - not supported in iTerm2 backend."""
        return False
    
    async def show_pane(
        self,
        _pane_id: str,
        _target_window_or_pane: str,
        _use_external_session: bool = False,
    ) -> bool:
        """Stub for showing a hidden pane - not supported in iTerm2 backend."""
        return False


def create_iterm_backend() -> ITermPaneBackend:
    """Creates an ITermBackend instance."""
    return ITermPaneBackend()
