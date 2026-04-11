"""
REST API for direct shell execution.
Provides a terminal-like interface from the WebUI.
"""
import asyncio
import os
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/shell", tags=["shell"])

ShellType = Literal["bash", "powershell", "cmd", "auto"]


class ShellRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    shell: ShellType = "auto"
    timeout: Optional[int] = 120000


class ShellResponse(BaseModel):
    output: str
    isError: bool
    metadata: Optional[dict] = None


class CwdResponse(BaseModel):
    cwd: str


@router.post("", response_model=ShellResponse)
async def execute_shell(request: ShellRequest) -> ShellResponse:
    """
    Execute a shell command.
    """
    if not request.command:
        raise HTTPException(status_code=400, detail="Missing command")

    # Determine the shell to use
    if request.shell == "auto":
        if os.name == "nt":
            request.shell = "powershell"
        else:
            request.shell = "bash"

    # Build the command
    if request.shell == "powershell":
        cmd = ["powershell", "-NoProfile", "-Command", request.command]
    elif request.shell == "cmd":
        cmd = ["cmd", "/c", request.command]
    elif request.shell == "bash":
        cmd = ["bash", "-c", request.command]
    else:
        cmd = request.command.split() if isinstance(request.command, str) else request.command

    # Set the working directory
    cwd = request.cwd or os.getcwd()

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=request.timeout / 1000 if request.timeout else 120.0,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise HTTPException(status_code=408, detail="Command timed out")

        output = stdout.decode("utf-8", errors="replace")
        error_output = stderr.decode("utf-8", errors="replace")

        return ShellResponse(
            output=output + error_output if error_output else output,
            isError=process.returncode != 0,
            metadata={
                "returncode": process.returncode,
                "cwd": cwd,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cwd", response_model=CwdResponse)
async def get_cwd() -> CwdResponse:
    """
    Get current working directory.
    """
    return CwdResponse(cwd=os.getcwd())
