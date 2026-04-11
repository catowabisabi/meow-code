from typing import List, Optional
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/hooks", tags=["hooks"])


class ToolHookConfig(BaseModel):
    id: str
    tool_name: str
    event: str
    command: Optional[str] = None
    enabled: bool = True
    description: Optional[str] = None


class CreateHookRequest(BaseModel):
    tool_name: str
    event: str  # e.g., "pre-execution", "post-execution"
    command: str
    enabled: bool = True
    description: Optional[str] = None


class HookResponse(BaseModel):
    success: bool
    hook: Optional[ToolHookConfig] = None
    message: str


_hooks_storage: List[ToolHookConfig] = [
    ToolHookConfig(
        id=str(uuid.uuid4()),
        tool_name="Read",
        event="post-execution",
        command="",
        enabled=True,
        description="Read files from the filesystem",
    ),
    ToolHookConfig(
        id=str(uuid.uuid4()),
        tool_name="Write",
        event="post-execution",
        command="",
        enabled=True,
        description="Write content to files",
    ),
    ToolHookConfig(
        id=str(uuid.uuid4()),
        tool_name="Edit",
        event="post-execution",
        command="",
        enabled=True,
        description="Make edits to existing files",
    ),
    ToolHookConfig(
        id=str(uuid.uuid4()),
        tool_name="Bash",
        event="pre-execution",
        command="",
        enabled=True,
        description="Execute shell commands",
    ),
    ToolHookConfig(
        id=str(uuid.uuid4()),
        tool_name="Grep",
        event="post-execution",
        command="",
        enabled=True,
        description="Search file contents using regex",
    ),
    ToolHookConfig(
        id=str(uuid.uuid4()),
        tool_name="Glob",
        event="post-execution",
        command="",
        enabled=True,
        description="Find files by glob pattern",
    ),
]


@router.get("", response_model=List[ToolHookConfig])
async def list_hooks() -> List[ToolHookConfig]:
    return _hooks_storage


@router.post("", response_model=ToolHookConfig)
async def create_hook(request: CreateHookRequest) -> ToolHookConfig:
    """Create a new hook configuration for tool events."""
    hook_id = str(uuid.uuid4())
    hook = ToolHookConfig(
        id=hook_id,
        tool_name=request.tool_name,
        event=request.event,
        command=request.command,
        enabled=request.enabled,
        description=request.description,
    )
    _hooks_storage.append(hook)
    return hook


@router.delete("/{hook_id}", response_model=HookResponse)
async def delete_hook(hook_id: str) -> HookResponse:
    """Delete a hook by ID."""
    for i, hook in enumerate(_hooks_storage):
        if hook.id == hook_id:
            del _hooks_storage[i]
            return HookResponse(success=True, hook=hook, message=f"Hook '{hook_id}' deleted")
    return HookResponse(success=False, message=f"Hook '{hook_id}' not found")