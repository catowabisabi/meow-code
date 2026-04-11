from typing import Any, Dict

from ..types import ToolDef, ToolContext, ToolResult
from .execute import execute_powershell_command


POWERSHELL_TOOL_NAME = "powershell"


async def _execute_powershell(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    command = args.get("command", "")
    timeout = args.get("timeout", 120000)
    cwd = args.get("cwd", None)

    if not command:
        return ToolResult(
            tool_call_id="",
            output="No command provided",
            is_error=True,
        )

    def abort_check() -> bool:
        return ctx.abort_signal() if ctx.abort_signal else False

    result = await execute_powershell_command(
        command=command,
        timeout=timeout,
        cwd=cwd or ctx.cwd,
        abort_signal=None,
        on_progress=None,
        auto_background=True,
        can_show_permission_prompts=True,
    )

    return ToolResult(
        tool_call_id="",
        output=result.output,
        is_error=result.is_error,
    )


def powershell_tool_def() -> ToolDef:
    return ToolDef(
        name=POWERSHELL_TOOL_NAME,
        description="Execute PowerShell commands on Windows",
        input_schema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The PowerShell command to execute",
                },
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in milliseconds (max 300000)",
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory for the command",
                },
            },
            "required": ["command"],
        },
        is_read_only=False,
        risk_level="medium",
        execute=_execute_powershell,
    )