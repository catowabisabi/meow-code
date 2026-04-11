"""
Shell execution tool — runs Bash/PowerShell/cmd commands.
This is the most powerful tool: direct OS command execution.
"""
import asyncio
import logging
import os
import signal
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..models.tool import ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class ShellInput:
    """Input schema for shell tool."""
    command: str
    timeout: int = 120000
    shell: str = "auto"
    cwd: Optional[str] = None
    use_sandbox: bool = True
    sandbox_disabled: bool = False
    run_in_background: bool = False


@dataclass
class ToolResult:
    """Result of tool execution."""
    output: str
    is_error: bool
    metadata: dict = field(default_factory=dict)


def get_shell_config(preference: str = "auto") -> tuple[str, list[str]]:
    """
    Determine shell command and arguments based on platform and preference.
    Returns (cmd, args) tuple.
    """
    is_windows = os.name == "nt"

    if preference == "powershell":
        return ("powershell.exe", ["-NoProfile", "-Command"])
    if preference == "bash":
        if is_windows:
            return ("bash.exe", ["-c"])
        return ("/bin/bash", ["-c"])
    if preference == "cmd":
        return ("cmd.exe", ["/c"])

    # auto: Windows defaults to PowerShell, others to bash
    if is_windows:
        return ("powershell.exe", ["-NoProfile", "-Command"])
    return ("/bin/bash", ["-c"])


async def _stream_read(
    reader: asyncio.StreamReader,
    callback: Optional[Callable[[str], None]] = None,
) -> str:
    """Read all output from a stream, optionally streaming to callback."""
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


async def execute_shell_command(
    input_data: ShellInput,
    cwd: Optional[str] = None,
    abort_signal: Optional[asyncio.Event] = None,
    on_progress: Optional[Callable[[dict], None]] = None,
) -> ToolResult:
    """
    Execute a shell command asynchronously.

    Args:
        input_data: ShellInput with command, timeout, shell, cwd
        cwd: Working directory (defaults to current directory)
        abort_signal: Optional event to check for abortion
        on_progress: Optional callback for streaming output {type: 'stdout'|'stderr', data: str}
    """
    cmd, args = get_shell_config(input_data.shell)
    timeout_seconds = input_data.timeout / 1000.0
    work_dir = input_data.cwd or cwd or os.getcwd()

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
        proc = await asyncio.create_subprocess_exec(
            cmd,
            *args,
            input_data.command,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )

        # Create timeout task
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
                # SIGTERM first
                proc.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # SIGKILL if still alive
                    proc.kill()
                    await proc.wait()
                return "", "[Process terminated: timeout]", -1

        # Check abort signal periodically
        async def check_abort():
            if abort_signal is None:
                return False
            while not abort_signal.is_set():
                await asyncio.sleep(0.1)
            return True

        # Run both tasks concurrently, abort takes priority
        stdout_text = ""
        stderr_text = ""
        returncode = 0

        if abort_signal:
            # Race between command completion and abort
            done, pending = await asyncio.wait(
                [asyncio.create_task(run_with_timeout())],
                timeout=timeout_seconds,
            )
            if not done:
                # Abort was signaled
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

    # Truncate large output
    max_len = 50000
    output = stdout_text
    if len(output) > max_len:
        output = output[:max_len] + f"\n... (truncated, {len(stdout_text)} total chars)"
    else:
        output = stdout_text

    # Append stderr if present
    if stderr_text:
        stderr_truncated = stderr_text[:10000]
        output = output + ("\n" if output else "") + f"[stderr]\n{stderr_truncated}"

    if killed:
        output = output + "\n[Process terminated: timeout or abort]"

    return ToolResult(
        output=output or "(no output)",
        is_error=returncode != 0 or killed,
        metadata={"exitCode": returncode, "killed": killed},
    )


def get_sandbox_config():
    """Get sandbox configuration for shell execution."""
    from ..sandbox.config import SandboxConfig
    return SandboxConfig.default()


async def execute_with_sandbox(
    input_data: ShellInput,
    cwd: Optional[str] = None,
    abort_signal: Optional[asyncio.Event] = None,
    on_progress: Optional[Callable[[dict], None]] = None,
) -> ToolResult:
    """
    Execute a shell command with sandbox isolation.
    
    This is the recommended execution path for untrusted commands.
    Falls back to non-sandboxed execution if sandbox is unavailable.
    """
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
    """
    Main shell execution entry point.
    
    Handles both foreground and background execution based on input_data.run_in_background.
    """
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


# Tool definition compatible with ToolDefinition model
shell_tool = ToolDefinition(
    name="shell",
    description=(
        "Execute shell commands on the user's computer. On Windows, defaults to PowerShell; "
        "on Linux/Mac, defaults to Bash. Use this for: running scripts, installing packages, "
        "git operations, file manipulation, running tests, builds, etc. "
        "Commands are sandboxed when possible for security."
    ),
    input_schema={
        "type": "object",
        "required": ["command"],
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
            "timeout": {
                "type": "number",
                "description": "Timeout in milliseconds (default: 120000)",
            },
            "shell": {
                "type": "string",
                "enum": ["bash", "powershell", "cmd", "auto"],
                "description": "Shell to use (default: auto)",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory (default: server cwd)",
            },
            "use_sandbox": {
                "type": "boolean",
                "description": "Enable sandbox isolation when available (default: true)",
            },
            "dangerouslyDisableSandbox": {
                "type": "boolean",
                "description": "Disable sandbox for this command (less secure, but may be needed for some commands)",
            },
            "run_in_background": {
                "type": "boolean",
                "description": "Run command in background, returns task ID for status tracking (default: false)",
            },
        },
    },
    is_read_only=False,
)
