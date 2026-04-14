"""Enhanced shell execution tool with CWD tracking - bridging gap with TypeScript Shell.ts"""
import asyncio
import logging
import os
import signal
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class CwdTracker:
    """
    Tracks current working directory state across shell commands.
    
    TypeScript equivalent: pwd(), setCwd(), setCwdState() from Shell.ts
    Python gap: No CWD tracking - cd in command has no effect.
    """
    _instance = None
    _cwd: str = ""
    _original_cwd: str = ""
    _cwd_history: List[str] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cwd = os.getcwd()
            cls._instance._original_cwd = os.getcwd()
            cls._instance._cwd_history = [cls._instance._cwd]
        return cls._instance
    
    def get(self) -> str:
        return self._cwd
    
    def get_original(self) -> str:
        return self._original_cwd
    
    def set(self, path: str) -> None:
        resolved = str(Path(path).resolve())
        if resolved != self._cwd:
            self._cwd = resolved
            self._cwd_history.append(resolved)
            logger.debug(f"CWD changed to: {resolved}")
    
    def is_valid(self) -> bool:
        return os.path.isdir(self._cwd)
    
    def recover_if_invalid(self) -> bool:
        if not self.is_valid():
            logger.warning(f"CWD {self._cwd} no longer exists, recovering to {self._original_cwd}")
            if os.path.isdir(self._original_cwd):
                self.set(self._original_cwd)
                return True
            return False
        return True
    
    def history(self) -> List[str]:
        return self._cwd_history.copy()


pwd = CwdTracker().get
setCwd = CwdTracker().set
getOriginalCwd = CwdTracker().get_original


@dataclass
class ShellInput:
    command: str
    timeout: int = 120000
    shell: str = "auto"
    cwd: Optional[str] = None
    use_sandbox: bool = True
    sandbox_disabled: bool = False
    run_in_background: bool = False
    prevent_cwd_changes: bool = False


@dataclass
class ToolResult:
    output: str
    is_error: bool
    metadata: dict = field(default_factory=dict)
    new_cwd: Optional[str] = None


@dataclass
class ShellProvider:
    """Abstraction for different shell types - bridges TypeScript ShellProvider interface"""
    shell_path: str
    shell_type: str  # "bash", "powershell", "cmd"
    
    def get_spawn_args(self, command: str) -> List[str]:
        raise NotImplementedError
    
    def build_exec_command(self, command: str, opts: Dict[str, Any]) -> tuple[str, str]:
        raise NotImplementedError
    
    def get_environment_overrides(self, command: str) -> Dict[str, str]:
        return {}
    
    detached: bool = False


class BashShellProvider(ShellProvider):
    def __init__(self, shell_path: str = "/bin/bash"):
        super().__init__(shell_path=shell_path, shell_type="bash")
    
    def get_spawn_args(self, command: str) -> List[str]:
        return ["-c", command]
    
    def build_exec_command(self, command: str, opts: Dict[str, Any]) -> tuple[str, str]:
        cwd = pwd()
        return command, cwd


class PowerShellProvider(ShellProvider):
    def __init__(self, shell_path: str = "powershell.exe"):
        super().__init__(shell_path=shell_path, shell_type="powershell")
    
    def get_spawn_args(self, command: str) -> List[str]:
        return ["-NoProfile", "-Command", command]
    
    def build_exec_command(self, command: str, opts: Dict[str, Any]) -> tuple[str, str]:
        cwd = pwd()
        return command, cwd


_shell_provider_cache: Optional[ShellProvider] = None


def get_shell_config(shell_type: str = "auto") -> ShellProvider:
    global _shell_provider_cache
    if _shell_provider_cache:
        return _shell_provider_cache
    
    is_windows = os.name == "nt"
    
    if shell_type == "powershell":
        _shell_provider_cache = PowerShellProvider()
    elif shell_type == "bash":
        if is_windows:
            _shell_provider_cache = BashShellProvider("bash.exe")
        else:
            _shell_provider_cache = BashShellProvider()
    elif shell_type == "cmd":
        _shell_provider_cache = ShellProvider(shell_path="cmd.exe", shell_type="cmd")
    else:
        if is_windows:
            _shell_provider_cache = PowerShellProvider()
        else:
            _shell_provider_cache = BashShellProvider()
    
    return _shell_provider_cache


def reset_shell_provider() -> None:
    global _shell_provider_cache
    _shell_provider_cache = None


async def _stream_read(
    reader: asyncio.StreamReader,
    callback: Optional[Callable[[str], None]] = None,
) -> str:
    chunks = []
    while True:
        try:
            chunk = await reader.read(8192)
            if not chunk:
                break
            text = chunk.decode("utf-8", errors="replace")
            chunks.append(text)
            if callback:
                callback(text)
        except Exception:
            break
    return "".join(chunks)


def _parse_cwd_from_output(output: str) -> Optional[str]:
    """
    Parse 'cd' commands from shell output to extract new CWD.
    This is a best-effort heuristic - TypeScript uses explicit pwd tracking.
    """
    lines = output.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line.startswith('__CLAUDE_CWD__='):
            return line.split('=', 1)[1].strip().strip("'\"")
    return None


async def execute_shell_command(
    input_data: ShellInput,
    cwd: Optional[str] = None,
    abort_signal: Optional[asyncio.Event] = None,
    on_progress: Optional[Callable[[dict], None]] = None,
) -> ToolResult:
    """
    Execute a shell command with CWD tracking.
    
    Enhanced from TypeScript Shell.ts exec() function.
    """
    provider = get_shell_config(input_data.shell)
    timeout_seconds = input_data.timeout / 1000.0
    
    cwd_tracker = CwdTracker()
    work_dir = input_data.cwd or cwd or cwd_tracker.get()
    
    if not cwd_tracker.is_valid():
        if not cwd_tracker.recover_if_invalid():
            return ToolResult(
                output=f"Working directory {work_dir} does not exist. Please restart from an existing directory.",
                is_error=True,
                metadata={"error": "invalid_cwd"},
            )
        work_dir = cwd_tracker.get()
    
    killed = False

    def progress_callback(data: str, stream_type: str):
        if on_progress:
            on_progress({
                "toolName": "shell",
                "toolId": "",
                "type": stream_type,
                "data": data,
            })

    try:
        cmd = provider.shell_path
        args = provider.get_spawn_args(input_data.command)
        
        proc = await asyncio.create_subprocess_exec(
            cmd,
            *args,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )

        async def run_with_timeout():
            nonlocal killed
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout_seconds,
                )
                stdout_text = stdout.decode("utf-8", errors="replace")
                stderr_text = stderr.decode("utf-8", errors="replace")
                return stdout_text, stderr_text, proc.returncode or 0
            except asyncio.TimeoutError:
                killed = True
                proc.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                return "", "[Process terminated: timeout]", -1

        stdout_text = ""
        stderr_text = ""
        returncode = 0

        if abort_signal:
            done, pending = await asyncio.wait(
                [asyncio.create_task(run_with_timeout())],
                timeout=timeout_seconds,
            )
            if not done:
                killed = True
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                stdout_text, stderr_text, returncode = "", "[Process terminated: abort]", -1
            else:
                for task in done:
                    stdout_text, stderr_text, returncode = task.result()
        else:
            stdout_text, stderr_text, returncode = await run_with_timeout()

    except FileNotFoundError as e:
        return ToolResult(
            output=f"Failed to execute command: {e}",
            is_error=True,
            metadata={"error": str(e)},
        )
    except Exception as e:
        return ToolResult(
            output=f"Failed to execute command: {e}",
            is_error=True,
            metadata={"error": str(e)},
        )

    if not input_data.prevent_cwd_changes:
        new_cwd = _parse_cwd_from_output(stdout_text)
        if new_cwd and os.path.isdir(new_cwd):
            cwd_tracker.set(new_cwd)

    max_len = 50000
    output = stdout_text
    if len(output) > max_len:
        output = output[:max_len] + f"\n... (truncated, {len(stdout_text)} total chars)"
    
    if stderr_text:
        stderr_truncated = stderr_text[:10000]
        output = output + ("\n" if output else "") + f"[stderr]\n{stderr_truncated}"

    if killed:
        output = output + "\n[Process terminated: timeout or abort]"

    return ToolResult(
        output=output or "(no output)",
        is_error=returncode != 0 or killed,
        metadata={"exitCode": returncode, "killed": killed},
        new_cwd=cwd_tracker.get() if not input_data.prevent_cwd_changes else None,
    )


def get_sandbox_config():
    from ..sandbox.config import SandboxConfig
    return SandboxConfig.default()


async def execute_with_sandbox(
    input_data: ShellInput,
    cwd: Optional[str] = None,
    abort_signal: Optional[asyncio.Event] = None,
    on_progress: Optional[Callable[[dict], None]] = None,
) -> ToolResult:
    if not input_data.use_sandbox or input_data.sandbox_disabled:
        return await execute_shell_command(input_data, cwd, abort_signal, on_progress)
    
    try:
        from ..sandbox.sandboxed_shell import SandboxedShellExecutor
        
        config = get_sandbox_config()
        executor = SandboxedShellExecutor(config=config)
        
        result = await executor.execute(
            input_data,
            cwd=cwd,
            abort_signal=abort_signal,
            on_progress=on_progress,
        )
        
        return result
        
    except Exception as e:
        logger.warning(f"Sandbox execution failed, falling back to unsafe: {e}")
        return await execute_shell_command(input_data, cwd, abort_signal, on_progress)


async def execute_shell(
    input_data: ShellInput,
    cwd: Optional[str] = None,
    abort_signal: Optional[asyncio.Event] = None,
    on_progress: Optional[Callable[[dict], None]] = None,
) -> ToolResult:
    if input_data.run_in_background:
        from .shell_task import get_background_executor
        executor = get_background_executor()
        _, result = await executor.execute_background(
            input_data,
            cwd=cwd,
            on_progress=on_progress,
        )
        return result
    
    if input_data.use_sandbox and not input_data.sandbox_disabled:
        return await execute_with_sandbox(input_data, cwd, abort_signal, on_progress)
    
    return await execute_shell_command(input_data, cwd, abort_signal, on_progress)
