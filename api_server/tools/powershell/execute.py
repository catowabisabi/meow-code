import asyncio
import os
import platform
import re
import signal
from typing import Callable, Optional

from .permissions import check_powershell_command
from .semantics import classify_command, has_sync_security_concerns, is_read_only_command
from .types import PowerShellResult, CommandCategory


DISALLOWED_AUTO_BACKGROUND_COMMANDS: set[str] = {
    "start-sleep",
    "sleep",
}

PROGRESS_THRESHOLD_MS: int = 2000
PROGRESS_INTERVAL_MS: int = 1000
ASSISTANT_BLOCKING_BUDGET_MS: int = 15_000


def detect_blocked_sleep_pattern(command: str) -> Optional[str]:
    first = command.strip().split(r"[;|&\r\n]")[0] or ""
    first = first.strip()
    m = re.match(
        r"^(?:start-sleep|sleep)(?:\s+-s(?:econds)?)?\s+(\d+)\s*$",
        first,
        re.IGNORECASE,
    )
    if not m:
        return None
    secs = int(m.group(1))
    if secs < 2:
        return None
    rest = command.strip()[len(first):].replace(r"^[\s;|&]+", "", 1)
    if rest:
        return f"Start-Sleep {secs} followed by: {rest}"
    return f"standalone Start-Sleep {secs}"


def is_autobackgrounding_allowed(command: str) -> bool:
    tokens = command.strip().split()
    if not tokens:
        return True
    first_word = tokens[0]
    from .canonical import resolve_to_canonical
    canonical = resolve_to_canonical(first_word)
    return canonical not in DISALLOWED_AUTO_BACKGROUND_COMMANDS


def _get_powershell_path() -> Optional[str]:
    if platform.system() != "Windows":
        return None
    return "powershell.exe"


async def execute_powershell_command(
    command: str,
    timeout: int = 120000,
    cwd: Optional[str] = None,
    abort_signal: Optional[asyncio.Event] = None,
    on_progress: Callable[[dict], None] | None = None,
    auto_background: bool = True,
    can_show_permission_prompts: bool = True,
) -> PowerShellResult:
    category = classify_command(command)
    is_read_only = is_read_only_command(command)

    permission_ok, permission_msg = check_powershell_command(command)
    if not permission_ok:
        return PowerShellResult(
            output=f"Permission denied: {permission_msg}",
            is_error=True,
            exit_code=1,
            category=category,
            is_read_only=is_read_only,
            metadata={"permission_denied": True, "reason": permission_msg},
        )

    sync_security_concern = has_sync_security_concerns(command)
    if sync_security_concern:
        if isinstance(sync_security_concern, str):
            return PowerShellResult(
                output=f"Security concern detected: {sync_security_concern}",
                is_error=True,
                exit_code=1,
                category=category,
                is_read_only=is_read_only,
                metadata={"security_concern": sync_security_concern},
            )

    blocked_sleep = detect_blocked_sleep_pattern(command)
    if blocked_sleep and auto_background:
        return PowerShellResult(
            output=f"Blocked: {blocked_sleep}. Run blocking commands in the background with run_in_background: true.",
            is_error=True,
            exit_code=1,
            category=category,
            is_read_only=is_read_only,
            metadata={"blocked_sleep": True, "reason": blocked_sleep},
        )

    ps_path = _get_powershell_path()
    if not ps_path:
        return PowerShellResult(
            output="PowerShell is not available on this system.",
            is_error=True,
            exit_code=0,
            category=category,
            is_read_only=is_read_only,
            metadata={"not_available": True},
        )

    work_dir = cwd or os.getcwd()
    cmd = [ps_path, "-NoProfile", "-Command", command]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout / 1000.0,
            )
            stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""
            returncode = proc.returncode or 0
        except asyncio.TimeoutError:
            proc.send_signal(signal.SIGTERM)
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            return PowerShellResult(
                output="[Process terminated: timeout]",
                is_error=True,
                exit_code=124,
                category=category,
                is_read_only=is_read_only,
                metadata={"timeout": True},
            )

        output = stdout_text
        if stderr_text:
            output += f"\n[stderr]\n{stderr_text[:5000]}"

        return PowerShellResult(
            output=output or "(no output)",
            is_error=returncode != 0,
            exit_code=returncode,
            category=category,
            is_read_only=is_read_only,
            metadata={"stderr_snippet": stderr_text[:5000] if stderr_text else ""},
        )
    except Exception as e:
        return PowerShellResult(
            output=f"Error: {e}",
            is_error=True,
            exit_code=1,
            category=category,
            is_read_only=is_read_only,
            metadata={"exception": str(e)},
        )