"""Worktree tools - manage git worktrees."""
import subprocess
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


async def _enter_worktree(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    branch = args.get('branch')
    path = args.get('path')
    
    if not branch:
        return ToolResult(tool_call_id=tool_call_id, output="branch is required", is_error=True)
    
    try:
        result = subprocess.run(
            ["git", "worktree", "add", path or branch, branch],
            capture_output=True,
            text=True,
            cwd=ctx.cwd,
        )
        
        if result.returncode == 0:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Created worktree for {branch} at {path or branch}",
                is_error=False,
            )
        else:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Failed to create worktree: {result.stderr}",
                is_error=True,
            )
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Error: {e}", is_error=True)


async def _exit_worktree(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    path = args.get('path')
    
    if not path:
        return ToolResult(tool_call_id=tool_call_id, output="path is required", is_error=True)
    
    try:
        result = subprocess.run(
            ["git", "worktree", "remove", path],
            capture_output=True,
            text=True,
            cwd=ctx.cwd,
        )
        
        if result.returncode == 0:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Removed worktree at {path}",
                is_error=False,
            )
        else:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Failed to remove worktree: {result.stderr}",
                is_error=True,
            )
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Error: {e}", is_error=True)


async def _list_worktrees(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    try:
        result = subprocess.run(
            ["git", "worktree", "list"],
            capture_output=True,
            text=True,
            cwd=ctx.cwd,
        )
        
        if result.returncode == 0:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=result.stdout,
                is_error=False,
            )
        else:
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Failed to list worktrees: {result.stderr}",
                is_error=True,
            )
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Error: {e}", is_error=True)


ENTER_WORKTREE_TOOL = ToolDef(
    name="enter_worktree",
    description="Create and enter a git worktree for working on a branch in isolation.",
    input_schema={
        "type": "object",
        "properties": {
            "branch": {"type": "string", "description": "Branch name"},
            "path": {"type": "string", "description": "Worktree path (defaults to branch name)"},
        },
        "required": ["branch"],
    },
    is_read_only=False,
    risk_level="high",
    execute=_enter_worktree,
)


EXIT_WORKTREE_TOOL = ToolDef(
    name="exit_worktree",
    description="Remove a git worktree.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Worktree path to remove"},
        },
        "required": ["path"],
    },
    is_read_only=False,
    risk_level="high",
    execute=_exit_worktree,
)


LIST_WORKTREES_TOOL = ToolDef(
    name="list_worktrees",
    description="List all git worktrees.",
    input_schema={
        "type": "object",
        "properties": {},
    },
    is_read_only=True,
    risk_level="low",
    execute=_list_worktrees,
)


__all__ = ["ENTER_WORKTREE_TOOL", "EXIT_WORKTREE_TOOL", "LIST_WORKTREES_TOOL"]
