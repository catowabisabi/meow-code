"""PowerShell execution tool.

Based on TypeScript PowerShellTool implementation.
Executes PowerShell commands with permission checking.
"""
import asyncio
import os
import signal
import re
from typing import Callable, Optional

from .command_semantics import interpret_command_result
from .destructive_command_warning import get_destructive_command_warning
from .path_validation import check_path_constraints
from .read_only_validation import has_sync_security_concerns
from .powershell_security import powershell_command_is_safe
from .read_only_validation import is_read_only_command
from .types import ToolDef, ToolContext, ToolResult

POWERSHELL_TOOL_NAME = "powershell"

DANGEROUS_REMOVAL_PATHS = {'/', '/etc', '/usr', '/bin', '/sbin', '/tmp', '/var', '/home'}

MAX_TIMEOUT_MS = 600000
DEFAULT_TIMEOUT_MS = 120000


def _is_dangerous_removal_path(path: str) -> bool:
    normalized = path.replace('\\', '/').replace("'", '').replace('"', '')
    for dangerous in DANGEROUS_REMOVAL_PATHS:
        if normalized == dangerous or normalized.startswith(dangerous + '/'):
            return True
    return False


async def execute_powershell_command(
    command: str,
    timeout: int = 120000,
    cwd: str | None = None,
    abort_signal=None,
    on_progress: Callable[[dict], None] | None = None,
    allowed_directories: Optional[list] = None,
    skip_security_checks: bool = False,
    skip_path_checks: bool = False,
) -> dict:
    if not command.strip():
        return {
            "output": "",
            "is_error": False,
            "metadata": {"exitCode": 0},
            "validation": {"is_read_only": True},
        }

    if not skip_security_checks:
        security_result = powershell_command_is_safe(command, None)
        if security_result.get('behavior') == 'ask':
            destructive_warning = get_destructive_command_warning(command)
            warning_msg = security_result.get('message', '')
            if destructive_warning:
                warning_msg = f"{warning_msg}. {destructive_warning}" if warning_msg else destructive_warning
            return {
                "output": "",
                "is_error": True,
                "metadata": {"exitCode": -1, "security_ask": True},
                "validation": {
                    "is_read_only": False,
                    "security_message": warning_msg,
                    "requires_approval": True,
                },
            }

    if not skip_path_checks:
        path_result = check_path_constraints(command, allowed_directories, cwd)
        if path_result.get('behavior') == 'deny':
            return {
                "output": "",
                "is_error": True,
                "metadata": {"exitCode": -1, "path_denied": True},
                "validation": {
                    "is_read_only": False,
                    "path_message": path_result.get('message'),
                    "requires_approval": True,
                },
            }
        if path_result.get('behavior') == 'ask':
            return {
                "output": "",
                "is_error": False,
                "metadata": {"exitCode": -1, "path_ask": True},
                "validation": {
                    "is_read_only": False,
                    "path_message": path_result.get('message'),
                    "requires_approval": True,
                },
            }

    cmd = ["powershell.exe", "-NoProfile", "-Command", command]
    work_dir = cwd or os.getcwd()

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
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")
            returncode = proc.returncode or 0
        except asyncio.TimeoutError:
            proc.send_signal(signal.SIGTERM)
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            return {
                "output": "[Process terminated: timeout]",
                "is_error": True,
                "metadata": {"timeout": True, "exitCode": -1},
                "validation": {"is_read_only": False},
            }

        output = stdout_text
        if stderr_text:
            output += f"\n[stderr]\n{stderr_text[:5000]}"

        semantic = interpret_command_result(command, returncode, stdout_text, stderr_text)
        is_error = semantic.get('isError', returncode != 0)

        destructive_warning = get_destructive_command_warning(command)

        is_read_only = is_read_only_command(command)

        return {
            "output": output or "(no output)",
            "is_error": is_error,
            "metadata": {
                "exitCode": returncode,
                "semantic_message": semantic.get('message'),
                "destructive_warning": destructive_warning,
            },
            "validation": {
                "is_read_only": is_read_only,
            },
        }
    except Exception as e:
        return {
            "output": f"Error: {e}",
            "is_error": True,
            "metadata": {"exitCode": -1},
            "validation": {"is_read_only": False},
        }


async def powershell_tool(
    command: str,
    timeout: int = 120000,
    cwd: str | None = None,
    allowed_directories: Optional[list] = None,
    skip_security_checks: bool = False,
    skip_path_checks: bool = False,
) -> dict:
    return await execute_powershell_command(
        command,
        timeout,
        cwd,
        allowed_directories=allowed_directories,
        skip_security_checks=skip_security_checks,
        skip_path_checks=skip_path_checks,
    )


def validate_powershell_command(
    command: str,
    allowed_directories: Optional[list] = None,
    cwd: Optional[str] = None,
) -> dict:
    if not command.strip():
        return {
            "valid": True,
            "is_read_only": True,
            "security_concerns": [],
            "path_issues": [],
            "requires_approval": False,
        }

    concerns = []
    path_issues = []
    requires_approval = False

    security_result = powershell_command_is_safe(command, None)
    if security_result.get('behavior') == 'ask':
        concerns.append(security_result.get('message', 'Security concern detected'))
        requires_approval = True

    sync_security = has_sync_security_concerns(command)
    if sync_security:
        concerns.append("Command contains sync security concerns (subexpressions, splatting, etc.)")
        requires_approval = True

    path_result = check_path_constraints(command, allowed_directories, cwd)
    if path_result.get('behavior') == 'deny':
        path_issues.append(path_result.get('message', 'Path denied'))
        requires_approval = True
    elif path_result.get('behavior') == 'ask':
        path_issues.append(path_result.get('message', 'Path requires approval'))
        requires_approval = True

    parts = re.split(r'\s*[;|]\s*', command)
    for segment in parts:
        tokens = segment.strip().split()
        if tokens and tokens[0].lower() in ('remove-item', 'rm', 'del', 'rd', 'ri'):
            for token in tokens[1:]:
                if token.startswith('-'):
                    continue
                if _is_dangerous_removal_path(token):
                    path_issues.append(f"Dangerous removal path: {token}")
                    requires_approval = True

    is_read_only = is_read_only_command(command) and not requires_approval

    destructive_warning = get_destructive_command_warning(command)
    if destructive_warning:
        concerns.append(destructive_warning)

    return {
        "valid": True,
        "is_read_only": is_read_only,
        "security_concerns": concerns,
        "path_issues": path_issues,
        "destructive_warning": destructive_warning,
        "requires_approval": requires_approval,
    }


def get_powershell_security_issues(command: str) -> list:
    issues = []
    security_result = powershell_command_is_safe(command, None)
    if security_result.get('behavior') == 'ask':
        issues.append(security_result.get('message', 'Security concern'))
    return issues


def is_powershell_command_read_only(command: str) -> bool:
    if not command.strip():
        return True
    if has_sync_security_concerns(command):
        return False
    return is_read_only_command(command)


async def _powershell_execute(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""

    command = args.get("command", "")
    timeout = args.get("timeout", 120000)
    cwd = args.get("cwd")
    allowed_directories = args.get("allowed_directories")
    skip_security_checks = args.get("skip_security_checks", False)
    skip_path_checks = args.get("skip_path_checks", False)

    if not command:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: command is required",
            is_error=True,
        )

    try:
        result = await powershell_tool(
            command=command,
            timeout=timeout,
            cwd=cwd,
            allowed_directories=allowed_directories,
            skip_security_checks=skip_security_checks,
            skip_path_checks=skip_path_checks,
        )

        return ToolResult(
            tool_call_id=tool_call_id,
            output=result.get("output", ""),
            is_error=result.get("is_error", False),
            metadata=result.get("metadata", {}),
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"PowerShell error: {str(e)}",
            is_error=True,
        )


POWERSHELL_TOOL = ToolDef(
    name=POWERSHELL_TOOL_NAME,
    description="Execute PowerShell commands on Windows. Provides secure PowerShell command execution with timeout, path validation, and security checks.",
    input_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The PowerShell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in milliseconds (default: 120000, max: 600000)",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command",
            },
            "allowed_directories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of allowed directory paths for file operations",
            },
            "skip_security_checks": {
                "type": "boolean",
                "description": "Skip security validation (less secure)",
            },
            "skip_path_checks": {
                "type": "boolean",
                "description": "Skip path constraint validation",
            },
        },
        "required": ["command"],
    },
    is_read_only=False,
    risk_level="high",
    execute=_powershell_execute,
)


__all__ = [
    "POWERSHELL_TOOL",
    "powershell_tool",
    "execute_powershell_command",
    "validate_powershell_command",
    "get_powershell_security_issues",
    "is_powershell_command_read_only",
]