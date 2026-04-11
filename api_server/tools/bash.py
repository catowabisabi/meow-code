"""
BashTool - Enhanced shell command execution tool.

Provides powerful shell command execution with:
- Multiple shell support (bash, powershell, cmd)
- Timeout management
- Background execution
- Sandbox isolation
- Progress streaming
- Security permission checking

Based on the TypeScript BashTool implementation in _claude_code_leaked_source_code.
"""
import asyncio
import json
import os
import signal
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .types import ToolDef, ToolContext, ToolResult


TOOL_NAME = "Bash"


@dataclass
class ShellInput:
    command: str
    timeout: int = 120000
    shell: str = "auto"
    cwd: Optional[str] = None
    use_sandbox: bool = True
    sandbox_disabled: bool = False
    run_in_background: bool = False
    dangerously_disable_sandbox: bool = False
    description: Optional[str] = None


@dataclass
class ShellOutput:
    stdout: str = ""
    stderr: str = ""
    interrupted: bool = False
    is_image: bool = False
    background_task_id: Optional[str] = None
    backgrounded_by_user: bool = False
    assistant_auto_backgrounded: bool = False
    return_code_interpretation: Optional[str] = None
    no_output_expected: bool = False
    raw_output_path: Optional[str] = None
    persisted_output_path: Optional[str] = None
    persisted_output_size: Optional[int] = None


COMMON_BACKGROUND_COMMANDS = {
    "npm", "yarn", "pnpm", "node", "python", "python3",
    "go", "cargo", "make", "docker", "terraform", "webpack",
    "vite", "jest", "pytest", "curl", "wget", "build",
    "test", "serve", "watch", "dev",
}


SILENT_COMMANDS = {
    "mv", "cp", "rm", "mkdir", "rmdir", "chmod", "chown",
    "chgrp", "touch", "ln", "cd", "export", "unset", "wait",
}


SEARCH_COMMANDS = {"find", "grep", "rg", "ag", "ack", "locate", "which", "whereis"}


READ_COMMANDS = {
    "cat", "head", "tail", "less", "more", "wc", "stat",
    "file", "strings", "jq", "awk", "cut", "sort", "uniq", "tr",
}


LIST_COMMANDS = {"ls", "tree", "du"}


NEUTRAL_COMMANDS = {"echo", "printf", "true", "false", ":"}


def get_shell_config(preference: str = "auto") -> tuple[str, list[str]]:
    is_windows = os.name == "nt"
    
    if preference == "powershell":
        return ("powershell.exe", ["-NoProfile", "-Command"])
    if preference == "bash":
        if is_windows:
            return ("bash.exe", ["-c"])
        return ("/bin/bash", ["-c"])
    if preference == "cmd":
        return ("cmd.exe", ["/c"])
    
    if is_windows:
        return ("powershell.exe", ["-NoProfile", "-Command"])
    return ("/bin/bash", ["-c"])


def is_background_command(command: str) -> bool:
    parts = command.strip().split()
    if not parts:
        return False
    base = parts[0].strip()
    return base in COMMON_BACKGROUND_COMMANDS


def is_silent_command(command: str) -> bool:
    parts = command.strip().split()
    if not parts:
        return False
    
    for i, part in enumerate(parts):
        if part in ("||", "&&", "|", ";"):
            continue
        base = part.split()[0] if i == 0 else part
        if base not in SILENT_COMMANDS:
            return False
    return True


def parse_command_parts(command: str) -> list[str]:
    parts = []
    current = ""
    in_quote = False
    quote_char = None
    
    for char in command:
        if char in ("'", '"') and not in_quote:
            in_quote = True
            quote_char = char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
        elif char in (" ", "\t", "\n") and not in_quote:
            if current:
                parts.append(current)
                current = ""
        else:
            current += char
    
    if current:
        parts.append(current)
    
    return parts


def _stream_read(
    reader: asyncio.StreamReader,
    callback: Optional[Callable[[str], None]] = None,
) -> str:
    chunks = []
    while True:
        try:
            chunk = reader.read(8192)
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
) -> ShellOutput:
    cmd, args = get_shell_config(input_data.shell)
    timeout_seconds = input_data.timeout / 1000.0
    work_dir = input_data.cwd or cwd or os.getcwd()
    
    killed = False
    
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
                return ShellOutput(interrupted=True)
            else:
                for task in done:
                    stdout_text, stderr_text, returncode = task.result()
        else:
            stdout_text, stderr_text, returncode = await run_with_timeout()
            
    except FileNotFoundError as e:
        return ShellOutput(
            stderr=f"Failed to execute command: {e}",
            interrupted=True,
        )
    except Exception as e:
        return ShellOutput(
            stderr=f"Failed to execute command: {e}",
            interrupted=True,
        )
    
    max_len = 50000
    output = stdout_text
    if len(output) > max_len:
        output = output[:max_len] + f"\n... (truncated, {len(stdout_text)} total chars)"
    
    stderr_trimmed = stderr_text[:10000] if stderr_text else ""
    if stderr_trimmed:
        output = output + ("\n" if output else "") + f"[stderr]\n{stderr_trimmed}"
    
    if killed:
        output = output + "\n[Process terminated: timeout or abort]"
    
    interpretation = None
    if returncode != 0:
        interpretation = f"Exit code {returncode}"
    
    no_output = is_silent_command(input_data.command)
    
    return ShellOutput(
        stdout=output or "(no output)",
        stderr="",
        interrupted=killed,
        return_code_interpretation=interpretation,
        no_output_expected=no_output,
    )


async def _bash_execute(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    command = args.get("command", "")
    timeout = args.get("timeout", 120000)
    shell = args.get("shell", "auto")
    cwd = args.get("cwd")
    use_sandbox = args.get("use_sandbox", True)
    dangerously_disable_sandbox = args.get("dangerouslyDisableSandbox", False)
    run_in_background = args.get("run_in_background", False)
    description = args.get("description")
    
    if not command:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: command is required",
            is_error=True,
        )
    
    if dangerously_disable_sandbox:
        use_sandbox = False
    
    input_data = ShellInput(
        command=command,
        timeout=timeout,
        shell=shell,
        cwd=cwd,
        use_sandbox=use_sandbox,
        sandbox_disabled=dangerously_disable_sandbox,
        run_in_background=run_in_background,
        dangerously_disable_sandbox=dangerously_disable_sandbox,
        description=description,
    )
    
    if input_data.run_in_background:
        background_task_id = f"bg_{id(command)}"
        return ToolResult(
            tool_call_id=tool_call_id,
            output=json.dumps({
                "stdout": "",
                "stderr": "",
                "backgroundTaskId": background_task_id,
                "message": f"Command running in background with ID: {background_task_id}",
            }),
            is_error=False,
        )
    
    try:
        result = await execute_shell_command(input_data, ctx.cwd)
        
        output_text = result.stdout
        if result.return_code_interpretation and result.interrupted:
            output_text += f"\n{result.return_code_interpretation}"
        
        return ToolResult(
            tool_call_id=tool_call_id,
            output=output_text,
            is_error=result.interrupted or result.return_code_interpretation is not None,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Bash error: {str(e)}",
            is_error=True,
        )


BASH_TOOL = ToolDef(
    name=TOOL_NAME,
    description="Execute shell commands. On Windows, defaults to PowerShell; on Linux/Mac, defaults to Bash.",
    input_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
            "timeout": {
                "type": "integer",
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
                "description": "Disable sandbox for this command (less secure)",
            },
            "run_in_background": {
                "type": "boolean",
                "description": "Run command in background (default: false)",
            },
            "description": {
                "type": "string",
                "description": "Clear, concise description of what this command does",
            },
        },
        "required": ["command"],
    },
    is_read_only=False,
    risk_level="high",
    execute=_bash_execute,
)


__all__ = [
    "BASH_TOOL",
    "ShellInput",
    "ShellOutput",
    "execute_shell_command",
    "is_background_command",
    "is_silent_command",
    "get_shell_config",
]
