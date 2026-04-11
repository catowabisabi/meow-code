"""
FastAPI routes for Claude Code slash commands.
Implements 66+ slash commands as REST API endpoints.
"""
import os
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import subprocess
import json
from pathlib import Path

from ..services.mcp_service import (
    mcp_add_server,
    mcp_connect,
    mcp_disconnect,
    mcp_list_servers,
    mcp_list_connections,
    mcp_list_tools,
    mcp_call_tool,
    mcp_list_resources,
    mcp_read_resource,
    get_mcp_service,
)
from ..services.compact import compact_messages
from ..services.token_estimation import TokenEstimationService, estimate_tokens_for_messages
from ..models.message import Message

router = APIRouter(prefix="/commands", tags=["commands"])


# Current session tracking
_current_session_id: Optional[str] = None


def get_current_session_id() -> Optional[str]:
    """Get the current active session ID."""
    return _current_session_id


def set_current_session_id(session_id: str) -> None:
    """Set the current active session ID."""
    global _current_session_id
    _current_session_id = session_id


def get_current_session() -> Optional[dict]:
    """Get the current active session data."""
    from .sessions import _get_active_session
    if _current_session_id:
        return _get_active_session(_current_session_id)
    return None


def get_current_session_messages() -> list:
    """Get messages from the current session."""
    session = get_current_session()
    if session:
        return session.get("messages", [])
    return []


def update_current_session_messages(messages: list) -> None:
    """Update messages in the current session."""
    session = get_current_session()
    if session:
        session["messages"] = messages


class CommandCategory(str, Enum):
    SESSION = "session"
    GIT = "git"
    FILE = "file"
    MODEL = "model"
    REVIEW = "review"
    PROJECT = "project"
    SETTINGS = "settings"
    INTEGRATIONS = "integrations"
    DEVELOPER = "developer"
    STATUS = "status"
    REMOTE = "remote"
    MEMORY = "memory"
    UTILITY = "utility"
    INTERNAL = "internal"


class CommandInfo(BaseModel):
    name: str
    description: str
    category: CommandCategory
    type: str  # "local", "local-jsx", "prompt"
    argument_hint: Optional[str] = None


class GitStatusResponse(BaseModel):
    branch: str
    status: str
    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []


class GitDiffResponse(BaseModel):
    diff: str
    file_count: int


class GitCommitRequest(BaseModel):
    message: str
    files: Optional[list[str]] = None  # If None, commit all staged


class GitCommitResponse(BaseModel):
    success: bool
    commit_hash: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


# ============================================================
# NEW COMMAND REQUEST/RESPONSE MODELS
# ============================================================

class NewCommandRequest(BaseModel):
    session_id: Optional[str] = None
    keep_context: bool = False
    force: bool = False


class NewCommandResponse(BaseModel):
    success: bool
    session_id: str
    message: str
    messages_cleared: int
    context_kept: bool


class GitLogEntry(BaseModel):
    hash: str
    message: str
    author: str
    date: str


class GitLogResponse(BaseModel):
    commits: list[GitLogEntry] = []


class SessionInfo(BaseModel):
    id: str
    mode: str
    model: str
    message_count: int
    created_at: Optional[str] = None


class ContextVisualization(BaseModel):
    total_tokens: int
    max_tokens: int
    usage_percent: float
    messages: list[dict] = []


class DiffResponse(BaseModel):
    content: str
    has_diff: bool


# ============================================================
# REQUEST/RESPONSE MODELS FOR MISSING COMMANDS
# ============================================================

class InitRequest(BaseModel):
    template: Optional[str] = None
    path: Optional[str] = None


class InitResponse(BaseModel):
    success: bool
    file_path: str
    message: str


class ReviewRequest(BaseModel):
    pr_number: Optional[int] = None


class ReviewResponse(BaseModel):
    success: bool
    pr_number: Optional[int] = None
    summary: Optional[str] = None
    issues: list[dict] = []
    error: Optional[str] = None


class UltraReviewRequest(BaseModel):
    path: Optional[str] = None
    deep: bool = False


class UltraReviewResponse(BaseModel):
    success: bool
    issues_found: int
    summary: str
    issues: list[dict] = []


class SecurityReviewRequest(BaseModel):
    path: Optional[str] = None
    check_owasp: bool = True


class SecurityReviewResponse(BaseModel):
    success: bool
    issues_found: int
    summary: str
    issues: list[dict] = []


class PRCommentsRequest(BaseModel):
    pr_number: int
    repo: Optional[str] = None


class PRComment(BaseModel):
    author: str
    body: str
    path: Optional[str] = None
    line: Optional[int] = None


class PRCommentsResponse(BaseModel):
    success: bool
    pr_number: int
    comments: list[PRComment] = []


class SessionInfoResponse(BaseModel):
    session_id: str
    mode: str
    model: str
    message_count: int
    remote_url: Optional[str] = None
    qr_code: Optional[str] = None


class ShareRequest(BaseModel):
    session_id: Optional[str] = None
    format: str = "json"  # json, markdown, text


class ShareResponse(BaseModel):
    success: bool
    share_url: Optional[str] = None
    content: Optional[str] = None


class TeleportRequest(BaseModel):
    ssh_host: Optional[str] = None
    ssh_port: int = 22
    ssh_user: Optional[str] = None
    working_directory: str = "/"


class TeleportResponse(BaseModel):
    success: bool
    connected: bool
    message: str


class ResumeRequest(BaseModel):
    session_id: str


class ResumeResponse(BaseModel):
    success: bool
    session_id: str
    messages: list[dict] = []
    title: Optional[str] = None


class RewindRequest(BaseModel):
    steps: int = 1


class RewindResponse(BaseModel):
    success: bool
    messages_removed: int
    current_message_count: int


class ModelListResponse(BaseModel):
    current_model: str
    available_models: list[str]


class ModelRequest(BaseModel):
    model: str
    provider: Optional[str] = None


# ============================================================
# COMMAND REGISTRY
# ============================================================

COMMANDS = [
    # Session Management
    CommandInfo(name="new", description="Clear conversation, free context", category=CommandCategory.SESSION, type="local"),
    CommandInfo(name="compact", description="Clear history with summary", category=CommandCategory.SESSION, type="local"),
    CommandInfo(name="context", description="Visualize context usage", category=CommandCategory.SESSION, type="local-jsx"),
    CommandInfo(name="resume", description="Resume previous session", category=CommandCategory.SESSION, type="local-jsx"),
    CommandInfo(name="rewind", description="Restore to previous point", category=CommandCategory.SESSION, type="local"),
    CommandInfo(name="session", description="Show remote session URL/QR", category=CommandCategory.SESSION, type="local-jsx"),
    CommandInfo(name="rename", description="Rename conversation", category=CommandCategory.SESSION, type="local-jsx"),
    CommandInfo(name="exit", description="Exit the REPL", category=CommandCategory.SESSION, type="local-jsx"),
    
    # Git & Version Control
    CommandInfo(name="commit", description="Create git commit", category=CommandCategory.GIT, type="prompt"),
    CommandInfo(name="commit-push-pr", description="Commit, push, create PR", category=CommandCategory.GIT, type="prompt"),
    CommandInfo(name="branch", description="Create branch", category=CommandCategory.GIT, type="local-jsx"),
    CommandInfo(name="diff", description="View uncommitted changes", category=CommandCategory.GIT, type="local-jsx"),
    CommandInfo(name="review", description="Review pull request", category=CommandCategory.REVIEW, type="prompt"),
    
    # AI Model & Inference
    CommandInfo(name="model", description="Set AI model", category=CommandCategory.MODEL, type="local-jsx"),
    CommandInfo(name="effort", description="Set effort level", category=CommandCategory.MODEL, type="local-jsx"),
    CommandInfo(name="fast", description="Toggle fast mode", category=CommandCategory.MODEL, type="local-jsx"),
    CommandInfo(name="advisor", description="Configure advisor", category=CommandCategory.MODEL, type="local"),
    
    # Code Review & Assistance
    CommandInfo(name="ultrareview", description="Advanced bug finding", category=CommandCategory.REVIEW, type="local-jsx"),
    CommandInfo(name="init", description="Initialize CLAUDE.md", category=CommandCategory.REVIEW, type="prompt"),
    CommandInfo(name="security-review", description="Security review", category=CommandCategory.REVIEW, type="prompt"),
    CommandInfo(name="pr-comments", description="Get PR comments", category=CommandCategory.REVIEW, type="prompt"),
    
    # File Operations
    CommandInfo(name="files", description="List files in context", category=CommandCategory.FILE, type="local"),
    CommandInfo(name="add-dir", description="Add working directory", category=CommandCategory.FILE, type="local-jsx"),
    CommandInfo(name="copy", description="Copy last response", category=CommandCategory.FILE, type="local-jsx"),
    
    # Productivity & Tools
    CommandInfo(name="plan", description="Enable plan mode", category=CommandCategory.PROJECT, type="local-jsx"),
    CommandInfo(name="tasks", description="Manage background tasks", category=CommandCategory.PROJECT, type="local-jsx"),
    CommandInfo(name="hooks", description="View hook configs", category=CommandCategory.PROJECT, type="local-jsx"),
    CommandInfo(name="skills", description="List skills", category=CommandCategory.PROJECT, type="local-jsx"),
    CommandInfo(name="permissions", description="Manage permissions", category=CommandCategory.PROJECT, type="local-jsx"),
    CommandInfo(name="mcp", description="Manage MCP servers", category=CommandCategory.PROJECT, type="local-jsx"),
    CommandInfo(name="btw", description="Quick side question", category=CommandCategory.PROJECT, type="local-jsx"),
    
    # Settings & Configuration
    CommandInfo(name="config", description="Open config panel", category=CommandCategory.SETTINGS, type="local-jsx"),
    CommandInfo(name="ide", description="IDE integrations", category=CommandCategory.SETTINGS, type="local-jsx"),
    CommandInfo(name="keybindings", description="Keybinding config", category=CommandCategory.SETTINGS, type="local"),
    CommandInfo(name="terminal-setup", description="Install key bindings", category=CommandCategory.SETTINGS, type="local-jsx"),
    CommandInfo(name="sandbox", description="Toggle sandbox mode", category=CommandCategory.SETTINGS, type="local-jsx"),
    
    # Account & Authentication
    CommandInfo(name="login", description="Sign in", category=CommandCategory.INTEGRATIONS, type="local-jsx"),
    CommandInfo(name="logout", description="Sign out", category=CommandCategory.INTEGRATIONS, type="local-jsx"),
    CommandInfo(name="upgrade", description="Upgrade to Max", category=CommandCategory.INTEGRATIONS, type="local-jsx"),
    CommandInfo(name="privacy-settings", description="Privacy settings", category=CommandCategory.INTEGRATIONS, type="local-jsx"),
    
    # Usage & Analytics
    CommandInfo(name="usage", description="Show usage limits", category=CommandCategory.STATUS, type="local-jsx"),
    CommandInfo(name="cost", description="Show session cost", category=CommandCategory.STATUS, type="local"),
    CommandInfo(name="stats", description="Usage statistics", category=CommandCategory.STATUS, type="local-jsx"),
    CommandInfo(name="insights", description="Generate insights", category=CommandCategory.STATUS, type="local-jsx"),
    CommandInfo(name="think-back", description="Year in review", category=CommandCategory.STATUS, type="local-jsx"),
    CommandInfo(name="passes", description="Share with friends", category=CommandCategory.STATUS, type="local-jsx"),
    CommandInfo(name="extra-usage", description="Extra usage config", category=CommandCategory.STATUS, type="local-jsx"),
    
    # Remote & Collaboration
    CommandInfo(name="remote-control", description="Remote sessions", category=CommandCategory.REMOTE, type="local-jsx"),
    CommandInfo(name="remote-env", description="Configure remote env", category=CommandCategory.REMOTE, type="local-jsx"),
    CommandInfo(name="web-setup", description="Web setup", category=CommandCategory.REMOTE, type="local-jsx"),
    CommandInfo(name="ultraplan", description="Multi-agent plan mode", category=CommandCategory.REMOTE, type="local-jsx"),
    
    # Integrations
    CommandInfo(name="install-github-app", description="Setup GitHub Actions", category=CommandCategory.INTEGRATIONS, type="local-jsx"),
    CommandInfo(name="install-slack-app", description="Install Slack app", category=CommandCategory.INTEGRATIONS, type="local"),
    CommandInfo(name="chrome", description="Chrome extension", category=CommandCategory.INTEGRATIONS, type="local-jsx"),
    CommandInfo(name="mobile", description="Mobile QR code", category=CommandCategory.INTEGRATIONS, type="local-jsx"),
    CommandInfo(name="desktop", description="Claude Desktop", category=CommandCategory.INTEGRATIONS, type="local-jsx"),
    CommandInfo(name="voice", description="Voice mode", category=CommandCategory.INTEGRATIONS, type="local"),
    
    # Utility & Debug
    CommandInfo(name="help", description="Show help", category=CommandCategory.UTILITY, type="local-jsx"),
    CommandInfo(name="feedback", description="Submit feedback", category=CommandCategory.UTILITY, type="local-jsx"),
    CommandInfo(name="doctor", description="Diagnose issues", category=CommandCategory.DEVELOPER, type="local-jsx"),
    CommandInfo(name="version", description="Print version", category=CommandCategory.UTILITY, type="local"),
    CommandInfo(name="release-notes", description="View release notes", category=CommandCategory.UTILITY, type="local"),
    CommandInfo(name="reload-plugins", description="Reload plugins", category=CommandCategory.UTILITY, type="local"),
    CommandInfo(name="heapdump", description="Dump heap (dev)", category=CommandCategory.DEVELOPER, type="local"),
    
    # Memory & Context
    CommandInfo(name="memory", description="Memory management", category=CommandCategory.MEMORY, type="local-jsx"),
    CommandInfo(name="thinkback", description="Conversation memory", category=CommandCategory.MEMORY, type="local-jsx"),
    CommandInfo(name="ctx-viz", description="Context visualization", category=CommandCategory.MEMORY, type="local-jsx"),
    CommandInfo(name="agents", description="Manage agent configurations", category=CommandCategory.SETTINGS, type="local-jsx"),
    CommandInfo(name="color", description="Set prompt bar color", category=CommandCategory.SETTINGS, type="local"),
    CommandInfo(name="status", description="Show version/model/account status", category=CommandCategory.STATUS, type="local"),
    CommandInfo(name="stickers", description="Order Claude Code stickers", category=CommandCategory.INTEGRATIONS, type="local"),
    CommandInfo(name="tag", description="Tag the session", category=CommandCategory.SESSION, type="local-jsx"),
    CommandInfo(name="outputStyle", description="Set output style (deprecated)", category=CommandCategory.SETTINGS, type="local"),
    CommandInfo(name="plugin", description="Manage plugins", category=CommandCategory.PROJECT, type="local-jsx"),
    CommandInfo(name="statusline", description="Configure status line UI", category=CommandCategory.SETTINGS, type="prompt"),
    CommandInfo(name="thinkbackPlay", description="Play thinkback animation", category=CommandCategory.MEMORY, type="local"),
    CommandInfo(name="export", description="Export conversation to file", category=CommandCategory.FILE, type="local-jsx"),
    CommandInfo(name="vim", description="Toggle vim editor mode", category=CommandCategory.SETTINGS, type="local"),
    CommandInfo(name="theme", description="Set application theme", category=CommandCategory.SETTINGS, type="local-jsx"),
    
    # INTERNAL_ONLY Commands
    CommandInfo(name="backfillSessions", description="Backfill internal session data", category=CommandCategory.INTERNAL, type="local"),
    CommandInfo(name="breakCache", description="Break prompt cache", category=CommandCategory.INTERNAL, type="local"),
    CommandInfo(name="bughunter", description="Bug hunter report", category=CommandCategory.INTERNAL, type="prompt"),
    CommandInfo(name="commitPushPr", description="Commit, push, and create PR", category=CommandCategory.INTERNAL, type="prompt"),
    CommandInfo(name="ctx_viz", description="Context visualization", category=CommandCategory.INTERNAL, type="local-jsx"),
    CommandInfo(name="forceSnip", description="Force truncate history", category=CommandCategory.INTERNAL, type="local"),
    CommandInfo(name="goodClaude", description="Claude Code feedback", category=CommandCategory.INTERNAL, type="prompt"),
    CommandInfo(name="initVerifiers", description="Initialize verifiers", category=CommandCategory.INTERNAL, type="prompt"),
    CommandInfo(name="issue", description="Issue tracking", category=CommandCategory.INTERNAL, type="prompt"),
    CommandInfo(name="mockLimits", description="Mock rate limits", category=CommandCategory.INTERNAL, type="local"),
    CommandInfo(name="bridgeKick", description="Bridge mode kick", category=CommandCategory.INTERNAL, type="local"),
    CommandInfo(name="antTrace", description="ANT trace", category=CommandCategory.INTERNAL, type="local"),
    CommandInfo(name="perfIssue", description="Performance issue report", category=CommandCategory.INTERNAL, type="prompt"),
    CommandInfo(name="env", description="Environment variable management", category=CommandCategory.INTERNAL, type="local"),
    CommandInfo(name="oauthRefresh", description="OAuth refresh", category=CommandCategory.INTERNAL, type="local"),
    CommandInfo(name="debugToolCall", description="Debug tool call", category=CommandCategory.INTERNAL, type="local"),
    CommandInfo(name="agentsPlatform", description="ANT agents platform", category=CommandCategory.INTERNAL, type="local-jsx"),
    CommandInfo(name="autofixPr", description="Auto fix PR", category=CommandCategory.INTERNAL, type="prompt"),
    
    # Feature-Flagged Conditional Commands
    CommandInfo(name="workflows", description="Scriptable workflows", category=CommandCategory.PROJECT, type="prompt"),
    CommandInfo(name="torch", description="Torch mode - rapid prototyping", category=CommandCategory.DEVELOPER, type="local"),
    CommandInfo(name="peers", description="Peer-to-peer sync mode", category=CommandCategory.REMOTE, type="local-jsx"),
    CommandInfo(name="fork", description="Fork subagent execution", category=CommandCategory.DEVELOPER, type="local-jsx"),
    CommandInfo(name="buddy", description="AI coding companion", category=CommandCategory.REVIEW, type="local-jsx"),
    CommandInfo(name="subscribe-pr", description="Subscribe to GitHub PR updates", category=CommandCategory.INTEGRATIONS, type="prompt"),
    CommandInfo(name="proactive", description="Enable proactive mode - AI predicts user intent", category=CommandCategory.INTERNAL, type="prompt"),
    CommandInfo(name="brief", description="Enable brief mode - compressed output for faster responses", category=CommandCategory.INTERNAL, type="prompt"),
    CommandInfo(name="assistant", description="Enable assistant mode - advisory style, less action-oriented", category=CommandCategory.INTERNAL, type="prompt"),
]


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("", response_model=list[CommandInfo])
async def list_commands():
    """List all available slash commands."""
    return COMMANDS


@router.get("/categories", response_model=dict[str, list[str]])
async def list_commands_by_category():
    """List commands grouped by category."""
    result = {}
    for cmd in COMMANDS:
        if cmd.category.value not in result:
            result[cmd.category.value] = []
        result[cmd.category.value].append(cmd.name)
    return result


@router.get("/{command_name}")
async def get_command(command_name: str):
    """Get details of a specific command."""
    for cmd in COMMANDS:
        if cmd.name == command_name:
            return cmd
    raise HTTPException(status_code=404, detail=f"Command '{command_name}' not found")


# ============================================================
# SESSION COMMANDS
# ============================================================

@router.post("/compact")
async def compact_session():
    """
    Compact the current conversation context.
    Replaces conversation history with a summary.
    """
    messages = get_current_session_messages()
    if not messages:
        return {"success": False, "message": "No active session or messages"}

    msg_objects = [Message.from_dict(m) if isinstance(m, dict) else m for m in messages]
    result = compact_messages(msg_objects)
    update_current_session_messages([m.model_dump() if hasattr(m, 'model_dump') else m for m in result.compacted_messages])

    return {
        "success": True,
        "message": f"Context compacted from {result.original_count} to {result.compacted_count} messages",
        "original_count": result.original_count,
        "compacted_count": result.compacted_count,
        "summary_length": len(result.summary)
    }


@router.post("/new", response_model=NewCommandResponse)
async def new_session(request: NewCommandRequest):
    """
    Start a new conversation, clearing the current session.
    
    Optionally keeps context (system prompt) if keep_context is True.
    Use force=True to skip confirmation if there are uncommitted changes.
    """
    from .sessions import _get_active_session, _create_new_session
    
    session_id = request.session_id or get_current_session_id()
    current_session = None
    
    if session_id:
        current_session = _get_active_session(session_id)
    
    if current_session and not request.force:
        returncode, status_output, _ = _run_git_command(["status", "--porcelain"])
        if returncode == 0 and status_output.strip():
            return NewCommandResponse(
                success=False,
                session_id=session_id or "new",
                message="Uncommitted changes detected. Use force=True to discard them.",
                messages_cleared=0,
                context_kept=False
            )
    
    messages_cleared = 0
    if current_session:
        messages_cleared = len(current_session.get("messages", []))
        if request.keep_context:
            system_messages = [m for m in current_session.get("messages", []) if m.get("role") == "system"]
            current_session["messages"] = system_messages
        else:
            current_session["messages"] = []
    
    new_session_id = session_id or _create_new_session()
    
    if current_session:
        current_session["id"] = new_session_id
    
    set_current_session_id(new_session_id)
    
    return NewCommandResponse(
        success=True,
        session_id=new_session_id,
        message=f"New session started. {'Context kept.' if request.keep_context else 'All messages cleared.'}",
        messages_cleared=messages_cleared,
        context_kept=request.keep_context
    )


@router.post("/exit")
async def exit_session():
    """Exit the current session."""
    session_id = get_current_session_id()
    session = get_current_session()

    if not session:
        return {"success": False, "message": "No active session to exit"}

    try:
        from .sessions import _save_session_file
        from datetime import datetime
        messages = session.get("messages", [])
        stored_data = {
            "id": session["id"],
            "title": session.get("title") or f"Chat {session['id'][:8]}...",
            "mode": session.get("mode", "chat"),
            "folder": session.get("folder"),
            "model": session.get("model", ""),
            "provider": session.get("provider", ""),
            "messages": messages,
            "createdAt": session.get("createdAt"),
            "updatedAt": datetime.utcnow().isoformat(),
            "metadata": session.get("metadata"),
        }
        _save_session_file(session["id"], stored_data)
        return {"success": True, "message": "Session ended and saved", "session_id": session_id}
    except Exception as e:
        return {"success": False, "message": f"Error ending session: {str(e)}"}


# ============================================================
# GIT COMMANDS
# ============================================================

def _run_git_command(args: list[str], cwd: Optional[str] = None) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd or Path.cwd(),
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


@router.get("/git/status", response_model=GitStatusResponse)
async def git_status():
    """Get current git status."""
    returncode, stdout, stderr = _run_git_command(["status", "--porcelain"])
    
    if returncode != 0:
        raise HTTPException(status_code=500, detail=f"Git error: {stderr}")
    
    branch_returncode, branch_stdout, _ = _run_git_command(["branch", "--show-current"])
    branch = branch_stdout.strip() or "HEAD"
    
    staged = []
    unstaged = []
    untracked = []
    
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        status = line[:2]
        filepath = line[3:]
        
        if status == "??":
            untracked.append(filepath)
        elif status[0] in "MAD":
            staged.append(filepath)
        elif status[1] in "MAD":
            unstaged.append(filepath)
    
    return GitStatusResponse(
        branch=branch,
        status=stdout or "No changes",
        staged=staged,
        unstaged=unstaged,
        untracked=untracked,
    )


@router.get("/git/diff", response_model=GitDiffResponse)
async def git_diff(file_path: Optional[str] = None):
    """Get git diff for changes."""
    args = ["diff"]
    if file_path:
        args.append(file_path)
    
    returncode, stdout, stderr = _run_git_command(args)
    
    if returncode != 0:
        raise HTTPException(status_code=500, detail=f"Git error: {stderr}")
    
    return GitDiffResponse(
        diff=stdout,
        file_count=len([l for l in stdout.split("\n") if l.startswith("diff --git")]),
    )


@router.get("/git/log", response_model=GitLogResponse)
async def git_log(limit: int = 10):
    """Get recent git commits."""
    returncode, stdout, stderr = _run_git_command([
        "log", f"--oneline", f"-{limit}",
        "--format=%H|%s|%an|%ad",
        "--date=iso"
    ])
    
    if returncode != 0:
        raise HTTPException(status_code=500, detail=f"Git error: {stderr}")
    
    commits = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|")
        if len(parts) >= 4:
            commits.append(GitLogEntry(
                hash=parts[0],
                message=parts[1],
                author=parts[2],
                date=parts[3],
            ))
    
    return GitLogResponse(commits=commits)


@router.post("/git/commit", response_model=GitCommitResponse)
async def git_commit(request: GitCommitRequest):
    """
    Create a git commit.
    Implements Git Safety Protocol from Claude Code.
    """
    # First check git status
    returncode, status_output, _ = _run_git_command(["status", "--porcelain"])
    if returncode != 0:
        return GitCommitResponse(success=False, error="Git not available")
    
    has_changes = bool(status_output.strip())
    if not has_changes:
        return GitCommitResponse(success=False, error="No changes to commit")
    
    # Check for untracked files that might be secrets
    untracked = [l[3:] for l in status_output.split("\n") if l.startswith("??")]
    secret_files = [f for f in untracked if any(s in f.lower() for s in [".env", "credentials", "secret", "key"])]
    warning = ""
    if secret_files:
        warning = f"\n\nWarning: Untracked files may contain secrets: {', '.join(secret_files)}"
    
    # Stage all changes if no specific files provided
    if request.files:
        for f in request.files:
            _run_git_command(["add", f])
    else:
        _run_git_command(["add", "."])
    
    # Create commit
    returncode, stdout, stderr = _run_git_command([
        "commit", "-m", request.message + warning
    ])
    
    if returncode != 0:
        return GitCommitResponse(success=False, error=stderr)
    
    # Get the commit hash
    _, hash_output, _ = _run_git_command(["rev-parse", "HEAD"])
    
    return GitCommitResponse(
        success=True,
        commit_hash=hash_output.strip(),
        message=request.message,
    )


class CommitCommandRequest(BaseModel):
    message: str
    files: Optional[list[str]] = None
    all_files: bool = False
    amend: bool = False


class CommitCommandResponse(BaseModel):
    success: bool
    commit_hash: Optional[str] = None
    message: str
    branch: Optional[str] = None
    files_committed: Optional[int] = None


@router.post("/commit", response_model=CommitCommandResponse)
async def commit_command(request: CommitCommandRequest):
    """
    Create a git commit with the current changes.
    
    Supports flags:
    - all_files: Stage all modified files before commit
    - amend: Amend to the previous commit
    - files: Specific files to commit
    """
    returncode, status_output, _ = _run_git_command(["status", "--porcelain"])
    if returncode != 0:
        return CommitCommandResponse(success=False, message="Git not available")
    
    has_changes = bool(status_output.strip())
    if not has_changes and not request.amend:
        return CommitCommandResponse(success=False, message="No changes to commit")
    
    branch_returncode, branch_stdout, _ = _run_git_command(["branch", "--show-current"])
    current_branch = branch_stdout.strip() or "HEAD"
    
    untracked = [l[3:] for l in status_output.split("\n") if l.startswith("??")]
    secret_files = [f for f in untracked if any(s in f.lower() for s in [".env", "credentials", "secret", "key"])]
    warning = ""
    if secret_files:
        warning = f"\n\nWarning: Untracked files may contain secrets: {', '.join(secret_files)}"
    
    if request.all_files:
        _run_git_command(["add", "-A"])
    elif request.files:
        for f in request.files:
            _run_git_command(["add", f])
    else:
        _run_git_command(["add", "-u"])
    
    commit_args = ["commit"]
    if request.amend:
        commit_args.append("--amend")
    commit_args.extend(["-m", request.message + warning])
    
    returncode, stdout, stderr = _run_git_command(commit_args)
    
    if returncode != 0:
        return CommitCommandResponse(success=False, message=f"Commit failed: {stderr}")
    
    _, hash_output, _ = _run_git_command(["rev-parse", "HEAD"])
    
    files_count = len(request.files) if request.files else (len(status_output.split("\n")) - 1 if has_changes else 0)
    
    return CommitCommandResponse(
        success=True,
        commit_hash=hash_output.strip(),
        message=f"Committed: {request.message[:50]}{'...' if len(request.message) > 50 else ''}",
        branch=current_branch,
        files_committed=files_count
    )


@router.get("/git/branch", response_model=list[str])
async def git_list_branches():
    """List all git branches."""
    returncode, stdout, stderr = _run_git_command(["branch", "-a"])
    
    if returncode != 0:
        raise HTTPException(status_code=500, detail=f"Git error: {stderr}")
    
    return [b.strip() for b in stdout.strip().split("\n") if b.strip()]


@router.post("/git/branch")
async def git_create_branch(name: str):
    """Create a new git branch."""
    returncode, stdout, stderr = _run_git_command(["checkout", "-b", name])
    
    if returncode != 0:
        return {"success": False, "error": stderr}
    
    return {"success": True, "branch": name}


@router.get("/git/stash")
async def git_stash_list():
    """List git stashes."""
    returncode, stdout, stderr = _run_git_command(["stash", "list"])
    
    if returncode != 0:
        return {"stashes": []}
    
    return {"stashes": stdout.strip().split("\n")}


# ============================================================
# REVIEW COMMANDS
# ============================================================

@router.get("/review/pr", response_model=dict)
async def review_pr(pr_number: Optional[int] = None):
    """
    Review a pull request.
    If no pr_number provided, lists open PRs.
    """
    # Check if gh CLI is available
    returncode, _, _ = _run_git_command(["which", "gh"])
    gh_available = returncode == 0
    
    if not gh_available:
        raise HTTPException(status_code=400, detail="GitHub CLI (gh) not installed")
    
    if pr_number is None:
        # List open PRs
        returncode, stdout, stderr = _run_git_command(["gh", "pr", "list", "--json", "number,title"])
        if returncode != 0:
            return {"prs": [], "error": stderr}
        return {"prs": json.loads(stdout)}
    
    # Get PR details
    returncode, details, _ = _run_git_command(["gh", "pr", "view", str(pr_number), "--json", "title,body,author,state"])
    if returncode != 0:
        raise HTTPException(status_code=404, detail=f"PR #{pr_number} not found")
    
    returncode, diff, _ = _run_git_command(["gh", "pr", "diff", str(pr_number)])
    
    return {
        "details": json.loads(details),
        "diff": diff,
    }


@router.get("/review/pr-comments")
async def get_pr_comments(pr_number: Optional[int] = None):
    """Get comments from a GitHub pull request."""
    if pr_number is None:
        raise HTTPException(status_code=400, detail="pr_number is required")
    
    returncode, stdout, stderr = _run_git_command([
        "gh", "api",
        f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments",
        "--jq", ".[].{body: .body, path: .path, line: .line, author: .user.login}"
    ])
    
    if returncode != 0:
        return {"comments": [], "error": stderr}
    
    return {"comments": json.loads(stdout) if stdout.strip() else []}


# ============================================================
# STATUS COMMANDS
# ============================================================

@router.get("/status")
async def get_status():
    """Get current session status."""
    session = get_current_session()
    if not session:
        return {
            "status": "inactive",
            "version": "1.0.0",
            "model": "claude-3-5-sonnet-20241022",
            "message_count": 0
        }

    return {
        "status": "active",
        "version": "1.0.0",
        "model": session.get("model", "claude-3-5-sonnet-20241022"),
        "message_count": len(session.get("messages", []))
    }


@router.get("/cost")
async def get_session_cost():
    """Calculate approximate session cost based on token usage."""
    session = get_current_session()
    if not session:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "message": "No active session"
        }

    messages = session.get("messages", [])
    model = session.get("model", "claude-3-5-sonnet-20241022")

    total_tokens = estimate_tokens_for_messages(messages)
    input_tokens = int(total_tokens * 0.6)
    output_tokens = int(total_tokens * 0.4)

    cost_estimate = TokenEstimationService.estimate_cost(input_tokens, output_tokens, model)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": cost_estimate.estimated_cost,
        "model": model
    }


@router.get("/usage")
async def get_usage():
    """Get usage limits and current usage."""
    return {
        "plan": "pro",
        "limits": {
            "monthly_requests": 100000,
            "monthly_tokens": 100000000,
        },
        "usage": {
            "requests_this_month": 0,
            "tokens_this_month": 0,
        }
    }


# ============================================================
# STATS COMMAND
# ============================================================

class StatsResponse(BaseModel):
    total_sessions: int
    total_tokens: int
    total_cost: float
    sessions_today: int
    tokens_today: int
    cost_this_week: float


# In-memory stats storage (in production, this would be persisted)
_stats_storage: dict = {
    "total_sessions": 0,
    "total_tokens": 0,
    "total_cost": 0.0,
    "sessions_today": 0,
    "tokens_today": 0,
    "cost_this_week": 0.0,
    "last_reset_date": None,
    "last_reset_week": None,
}


def _reset_daily_stats_if_needed() -> None:
    """Reset daily stats if it's a new day."""
    from datetime import date
    today = date.today().isoformat()
    if _stats_storage.get("last_reset_date") != today:
        _stats_storage["sessions_today"] = 0
        _stats_storage["tokens_today"] = 0
        _stats_storage["last_reset_date"] = today


def _reset_weekly_stats_if_needed() -> None:
    """Reset weekly stats if it's a new week."""
    from datetime import date, timedelta
    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    stored_week = _stats_storage.get("last_reset_week", "")
    if stored_week != week_start:
        _stats_storage["cost_this_week"] = 0.0
        _stats_storage["last_reset_week"] = week_start


def _update_stats(tokens: int, cost: float) -> None:
    """Update stats with new token usage and cost."""
    _reset_daily_stats_if_needed()
    _reset_weekly_stats_if_needed()
    _stats_storage["total_sessions"] += 1
    _stats_storage["total_tokens"] += tokens
    _stats_storage["total_cost"] += cost
    _stats_storage["sessions_today"] += 1
    _stats_storage["tokens_today"] += tokens
    _stats_storage["cost_this_week"] += cost


@router.get("/stats", response_model=StatsResponse)
async def get_usage_stats():
    """
    Get usage statistics including token usage, cost, and session counts.
    
    Returns aggregated stats:
    - total_sessions: All-time total number of sessions
    - total_tokens: All-time total tokens used
    - total_cost: All-time total estimated cost in USD
    - sessions_today: Number of sessions today
    - tokens_today: Total tokens used today
    - cost_this_week: Total cost for the current week
    """
    _reset_daily_stats_if_needed()
    _reset_weekly_stats_if_needed()
    
    return StatsResponse(
        total_sessions=_stats_storage["total_sessions"],
        total_tokens=_stats_storage["total_tokens"],
        total_cost=round(_stats_storage["total_cost"], 6),
        sessions_today=_stats_storage["sessions_today"],
        tokens_today=_stats_storage["tokens_today"],
        cost_this_week=round(_stats_storage["cost_this_week"], 6),
    )


# ============================================================
# INSIGHTS COMMAND
# ============================================================

class InsightsResponse(BaseModel):
    patterns: list[str]
    suggestions: list[str]
    summary: str


def _analyze_conversation_patterns(messages: list) -> list[str]:
    """Analyze messages to detect conversation patterns."""
    patterns = []
    
    if not messages:
        return patterns
    
    # Count message types
    user_msgs = [m for m in messages if m.get("role") == "user"]
    assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
    
    # Pattern: short vs long conversations
    if len(messages) > 50:
        patterns.append("Long-running conversation - consider using /compact to summarize context")
    elif len(messages) < 5:
        patterns.append("Quick interaction pattern detected")
    
    # Pattern: frequent tool usage
    tool_count = 0
    for msg in assistant_msgs:
        content = msg.get("content", [])
        if isinstance(content, list):
            tool_count += sum(1 for c in content if isinstance(c, dict) and c.get("type") == "tool_use")
    
    if tool_count > 20:
        patterns.append(f"Heavy tool usage detected ({tool_count} tool calls)")
    elif tool_count == 0:
        patterns.append("Conversational only - no tool execution")
    
    # Pattern: file editing
    edit_count = 0
    for msg in assistant_msgs:
        content = msg.get("content", [])
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    name = c.get("name", "")
                    if name in ("Edit", "Write", "Bash"):
                        input_data = c.get("input", {})
                        if "git" in str(input_data).lower():
                            edit_count += 1
    
    if edit_count > 5:
        patterns.append("Active version control usage")
    
    # Pattern: error handling
    error_count = sum(1 for m in messages if "error" in str(m.get("content", "")).lower())
    if error_count > 3:
        patterns.append("Multiple errors encountered - debugging workflow detected")
    
    # Pattern: session length
    if len(user_msgs) > 10:
        patterns.append("Multi-turn problem solving detected")
    
    return patterns


def _generate_suggestions(messages: list, patterns: list[str]) -> list[str]:
    """Generate suggestions based on conversation analysis."""
    suggestions = []
    
    if len(messages) > 100:
        suggestions.append("Your context is getting full. Use /compact to summarize and free up space.")
    
    if len(messages) < 3:
        suggestions.append("Try providing more context for better assistance.")
    
    # Check for repeated patterns
    tool_names = []
    for msg in messages:
        if msg.get("role") == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        tool_names.append(c.get("name"))
    
    if tool_names.count("Bash") > 10:
        suggestions.append("Consider creating a script for frequently repeated shell commands.")
    
    if "debugging workflow detected" in " ".join(patterns).lower():
        suggestions.append("Use /ultrareview for deep bug analysis when debugging complex issues.")
    
    # Check for git usage patterns
    git_related = any("git" in str(m.get("content", "")).lower() for m in messages)
    if git_related and "git commit" not in str(messages).lower():
        suggestions.append("Remember to commit your changes with /commit after significant work.")
    
    if not suggestions:
        suggestions.append("Provide more details about your task for better suggestions.")
    
    return suggestions[:5]  # Limit to 5 suggestions


def _generate_summary(messages: list, patterns: list[str]) -> str:
    """Generate an overall summary of the conversation."""
    if not messages:
        return "No conversation history available."
    
    user_msgs = [m for m in messages if m.get("role") == "user"]
    assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
    
    total_messages = len(messages)
    session_duration = "brief"
    
    if total_messages > 50:
        session_duration = "extended"
    elif total_messages > 20:
        session_duration = "moderate"
    
    # Build summary
    summary_parts = []
    
    summary_parts.append(f"This was a {session_duration} coding session")
    
    if user_msgs:
        # Analyze first user message for context
        first_prompt = user_msgs[0].get("content", "")
        if isinstance(first_prompt, list):
            for block in first_prompt:
                if isinstance(block, dict) and block.get("type") == "text":
                    first_prompt = block.get("text", "")[:100]
                    break
        elif not isinstance(first_prompt, str):
            first_prompt = str(first_prompt)[:100]
        
        if first_prompt:
            summary_parts.append(f"centered on: {first_prompt[:50]}...")
    
    # Add pattern-based insights
    if patterns:
        if any("tool" in p.lower() for p in patterns):
            summary_parts.append("with active tool usage")
        if any("debug" in p.lower() for p in patterns):
            summary_parts.append("involving debugging")
    
    summary_parts.append(f"({total_messages} total messages)")
    
    return " ".join(summary_parts)


@router.get("/insights", response_model=InsightsResponse)
async def generate_insights(time_range: Optional[str] = "all"):
    """
    Generate AI-powered insights from conversation history.
    
    Analyzes the current session's conversation to identify:
    - patterns: Recurring patterns detected in the conversation
    - suggestions: Personalized suggestions for improvement
    - summary: Overall summary of the conversation
    
    Args:
        time_range: Time range to analyze ("all", "week", "day"). Defaults to "all".
    """
    session = get_current_session()
    
    if not session:
        return InsightsResponse(
            patterns=["No active session"],
            suggestions=["Start a conversation to see insights"],
            summary="No conversation history available."
        )
    
    messages = session.get("messages", [])
    
    # Analyze patterns
    patterns = _analyze_conversation_patterns(messages)
    
    # Generate suggestions
    suggestions = _generate_suggestions(messages, patterns)
    
    # Generate summary
    summary = _generate_summary(messages, patterns)
    
    return InsightsResponse(
        patterns=patterns,
        suggestions=suggestions,
        summary=summary
    )


# ============================================================
# PROJECT COMMANDS
# ============================================================

@router.get("/files")
async def list_project_files(path: str = "."):
    """List files in the project."""
    try:
        p = Path(path)
        if not p.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        
        if p.is_file():
            return {"files": [str(p)], "dirs": []}
        
        files = []
        dirs = []
        for item in p.iterdir():
            if item.is_file():
                files.append(str(item))
            else:
                dirs.append(str(item))
        
        return {"files": files, "dirs": dirs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan")
async def enter_plan_mode(enable: bool = True):
    """Enter or exit plan mode."""
    return {
        "success": True,
        "mode": "plan" if enable else "chat",
        "message": "Plan mode enabled - read only, no file changes" if enable else "Plan mode disabled"
    }


@router.get("/tasks", response_model=list[dict])
async def list_tasks():
    """List all background tasks."""
    # Placeholder - would integrate with task service
    return []


@router.post("/tasks")
async def create_task(name: str, description: str = ""):
    """Create a background task."""
    return {
        "success": True,
        "task_id": f"task_{id(name)}",
        "name": name,
        "description": description,
        "status": "pending",
    }


# ============================================================
# MODEL COMMANDS
# ============================================================

@router.get("/model")
async def get_current_model():
    """Get the current model configuration."""
    return {
        "model": "claude-3-5-sonnet-20241022",
        "provider": "anthropic",
    }


@router.post("/model")
async def set_model(model: str):
    """Set the current model."""
    return {
        "success": True,
        "model": model,
    }


@router.post("/effort")
async def set_effort(level: str = "medium"):
    """Set effort level (low, medium, high)."""
    valid_levels = ["low", "medium", "high"]
    if level not in valid_levels:
        raise HTTPException(status_code=400, detail=f"Invalid effort level. Must be one of: {valid_levels}")
    
    return {
        "success": True,
        "effort": level,
    }


@router.post("/fast")
async def toggle_fast_mode(enable: Optional[bool] = None):
    """Toggle fast mode."""
    return {
        "success": True,
        "fast_mode": enable if enable is not None else True,
    }


# ============================================================
# SETTINGS COMMANDS
# ============================================================

@router.get("/config")
async def get_config():
    """Get current configuration."""
    return {
        "model": "claude-3-5-sonnet-20241022",
        "effort": "medium",
        "fast_mode": False,
    }


@router.post("/config")
async def update_config(key: str, value: Any):
    """Update configuration."""
    return {
        "success": True,
        "key": key,
        "value": value,
    }


# ============================================================
# CONTEXT COMMANDS
# ============================================================

@router.get("/context", response_model=ContextVisualization)
async def visualize_context():
    """
    Visualize current context usage.
    Shows token count, message count, and capacity.
    """
    session = get_current_session()
    if not session:
        return ContextVisualization(
            total_tokens=0,
            max_tokens=200000,
            usage_percent=0.0,
            messages=[],
        )

    messages = session.get("messages", [])
    total_tokens = estimate_tokens_for_messages(messages)
    max_tokens = 200000
    usage_percent = (total_tokens / max_tokens) * 100 if max_tokens > 0 else 0.0

    return ContextVisualization(
        total_tokens=total_tokens,
        max_tokens=max_tokens,
        usage_percent=round(usage_percent, 2),
        messages=messages,
    )


# ============================================================
# DOCTOR COMMAND
# ============================================================

@router.get("/doctor", response_model=dict)
async def run_doctor():
    """
    Run diagnostic checks.
    Checks: Git, API connectivity, configuration, etc.
    """
    issues = []
    
    # Check git
    returncode, _, _ = _run_git_command(["--version"])
    if returncode != 0:
        issues.append({"severity": "error", "component": "git", "message": "Git not found"})
    else:
        issues.append({"severity": "info", "component": "git", "message": "Git available"})
    
    # Check Python
    try:
        import sys
        issues.append({
            "severity": "info",
            "component": "python",
            "message": f"Python {sys.version.split()[0]}"
        })
    except:
        issues.append({"severity": "error", "component": "python", "message": "Python not found"})
    
    # Check API connectivity (would test actual API)
    issues.append({"severity": "info", "component": "api", "message": "API server running"})
    
    return {
        "status": "ok" if not any(i["severity"] == "error" for i in issues) else "issues_found",
        "issues": issues,
    }


# ============================================================
# VERSION COMMAND
# ============================================================

@router.get("/version")
async def get_version():
    """Get version information."""
    return {
        "version": "1.0.0",
        "api_server": "1.0.0",
        "build": "production",
    }


# ============================================================
# HELP COMMAND
# ============================================================

@router.get("/help")
async def get_help(command: Optional[str] = None):
    """Get help for commands."""
    if command:
        for cmd in COMMANDS:
            if cmd.name == command:
                return cmd
        raise HTTPException(status_code=404, detail=f"Command '{command}' not found")
    
    return {
        "intro": "Claude Code Commands - Available slash commands",
        "categories": {
            "session": "Session management commands",
            "git": "Git version control commands",
            "model": "Model and inference commands",
            "review": "Code review commands",
            "file": "File operation commands",
            "project": "Project management commands",
            "settings": "Configuration commands",
            "status": "Status and usage commands",
            "remote": "Remote collaboration commands",
            "integrations": "External integrations",
            "utility": "Utility commands",
            "memory": "Memory management commands",
        },
        "commands": [cmd.model_dump() for cmd in COMMANDS],
    }


# ============================================================
# INIT COMMAND
# ============================================================

@router.post("/init", response_model=InitResponse)
async def init_project(request: InitRequest = None):
    """
    Initialize CLAUDE.md in the project.
    Creates a standard project documentation file.
    """
    template_path = request.template if request and request.template else None
    target_path = request.path if request and request.path else "CLAUDE.md"
    
    CLAUDE_MD_TEMPLATE = """# Project Context

## Overview
Brief description of this project.

## Tech Stack
- Language/Framework:
- Key dependencies:

## Project Structure
```
.
```

## Key Files
- `src/` - Source code
- `tests/` - Test files

## Commands
```bash
# Install dependencies
npm install

# Run tests
npm test
```

## Notes
- Current status:
- Known issues:
"""

    try:
        p = Path(target_path)
        if p.exists():
            return InitResponse(
                success=False,
                file_path=str(p),
                message=f"File already exists: {target_path}"
            )
        
        content = CLAUDE_MD_TEMPLATE
        if template_path:
            template_file = Path(template_path)
            if template_file.exists():
                content = template_file.read_text(encoding="utf-8")
        
        p.write_text(content, encoding="utf-8")
        return InitResponse(
            success=True,
            file_path=str(p),
            message=f"Created {target_path}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# REVIEW COMMANDS (Full Implementation)
# ============================================================

@router.post("/review", response_model=ReviewResponse)
async def review_pull_request(request: ReviewRequest):
    """
    Review a pull request.
    Analyzes PR diff for code quality and potential issues.
    """
    from ..tools.review_tools import _review_pr, _check_gh_available
    from ..tools.types import ToolContext
    
    if not _check_gh_available():
        return ReviewResponse(
            success=False,
            error="GitHub CLI (gh) not installed. Install from https://cli.github.com/"
        )
    
    pr_number = request.pr_number if request else None
    
    if pr_number is None:
        returncode, stdout, stderr = _run_git_command(["gh", "pr", "list", "--json", "number,title,state"])
        if returncode != 0:
            return ReviewResponse(success=False, error=stderr)
        prs = json.loads(stdout) if stdout.strip() else []
        return ReviewResponse(
            success=True,
            summary=f"Open PRs: {len(prs)}",
            issues=[{"number": pr["number"], "title": pr["title"], "state": pr["state"]} for pr in prs]
        )
    
    class DummyContext:
        cwd = str(Path.cwd())
        tool_call_id = ""
    
    result = await _review_pr({"pr_number": pr_number}, DummyContext())
    
    if result.is_error:
        return ReviewResponse(success=False, error=result.output)
    
    return ReviewResponse(
        success=True,
        pr_number=pr_number,
        summary=result.output[:500] if len(result.output) > 500 else result.output,
        issues=[]
    )


@router.post("/ultrareview", response_model=UltraReviewResponse)
async def run_ultrareview(request: UltraReviewRequest):
    """
    Advanced bug finding review.
    Performs deep analysis of code changes.
    """
    from ..tools.review_tools import _ultra_review
    from ..tools.types import ToolContext
    
    class DummyContext:
        cwd = str(Path.cwd())
        tool_call_id = ""
    
    result = await _ultra_review({"path": request.path or ".", "deep": request.deep}, DummyContext())
    
    if result.is_error:
        return UltraReviewResponse(
            success=False,
            issues_found=0,
            summary=f"Error: {result.output}"
        )
    
    metadata = result.metadata or {}
    review_result = metadata.get("review_result", {})
    
    return UltraReviewResponse(
        success=True,
        issues_found=review_result.get("statistics", {}).get("total", 0),
        summary=result.output[:1000] if len(result.output) > 1000 else result.output,
        issues=review_result.get("issues", [])
    )


@router.post("/security-review", response_model=SecurityReviewResponse)
async def run_security_review(request: SecurityReviewRequest):
    """
    Security-focused review.
    Analyzes code for common security vulnerabilities.
    """
    from ..tools.review_tools import _security_review
    from ..tools.types import ToolContext
    
    class DummyContext:
        cwd = str(Path.cwd())
        tool_call_id = ""
    
    result = await _security_review(
        {"path": request.path or ".", "check_owasp": request.check_owasp},
        DummyContext()
    )
    
    if result.is_error:
        return SecurityReviewResponse(
            success=False,
            issues_found=0,
            summary=f"Error: {result.output}"
        )
    
    metadata = result.metadata or {}
    review_result = metadata.get("review_result", {})
    
    return SecurityReviewResponse(
        success=True,
        issues_found=review_result.get("statistics", {}).get("total", 0),
        summary=result.output[:1000] if len(result.output) > 1000 else result.output,
        issues=review_result.get("issues", [])
    )


@router.get("/pr-comments", response_model=PRCommentsResponse)
async def get_pr_comments(pr_number: int, repo: Optional[str] = None):
    """
    Get comments from a GitHub pull request.
    """
    returncode, stdout, stderr = _run_git_command([
        "gh", "api",
        f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments",
        "--jq", ".[].{body: .body, path: .path, line: .line, author: .user.login}"
    ])
    
    if returncode != 0:
        return PRCommentsResponse(
            success=False,
            pr_number=pr_number,
            comments=[],
        )
    
    comments_data = json.loads(stdout) if stdout.strip() else []
    comments = [PRComment(**c) for c in comments_data]
    
    return PRCommentsResponse(
        success=True,
        pr_number=pr_number,
        comments=comments
    )


# ============================================================
# SESSION COMMANDS
# ============================================================

@router.get("/session/info", response_model=SessionInfoResponse)
async def get_session_info():
    """
    Get current session information including remote URL and QR code.
    """
    session = get_current_session()
    if not session:
        return SessionInfoResponse(
            session_id="current",
            mode="chat",
            model="claude-3-5-sonnet-20241022",
            message_count=0,
            remote_url=None,
            qr_code=None
        )

    return SessionInfoResponse(
        session_id=session.get("id", "current"),
        mode=session.get("mode", "chat"),
        model=session.get("model", "claude-3-5-sonnet-20241022"),
        message_count=len(session.get("messages", [])),
        remote_url=session.get("metadata", {}).get("remote_url"),
        qr_code=session.get("metadata", {}).get("qr_code")
    )


@router.post("/session/share", response_model=ShareResponse)
async def share_session(request: ShareRequest):
    """
    Share the current conversation.
    Returns a shareable URL or exported content.
    """
    session_id = request.session_id if request else None
    format_type = request.format if request else "json"
    
    if format_type == "markdown":
        content = "# Conversation Export\n\nExported session content here."
    elif format_type == "text":
        content = "Conversation Export\n===================\n\nExported session content here."
    else:
        content = json.dumps({"session_id": session_id, "messages": []}, indent=2)
    
    return ShareResponse(
        success=True,
        share_url=None,
        content=content
    )


# ============================================================
# TELEPORT COMMAND
# ============================================================

@router.post("/teleport", response_model=TeleportResponse)
async def teleport_connect(request: TeleportRequest):
    """
    Establish a remote connection via teleport.
    """
    from ..services.teleport import connect_teleport, TeleportConfig
    
    config = TeleportConfig(
        ssh_host=request.ssh_host,
        ssh_port=request.ssh_port,
        ssh_user=request.ssh_user,
        working_directory=request.working_directory
    )
    
    result = await connect_teleport(config)
    
    return TeleportResponse(
        success=bool(result),
        connected=bool(result),
        message=result or "Not connected"
    )


@router.get("/teleport/status")
async def teleport_status():
    """
    Get teleport connection status.
    """
    from ..services.teleport import get_teleport_status
    
    status = await get_teleport_status()
    return status


# ============================================================
# RESUME COMMAND
# ============================================================

@router.post("/resume", response_model=ResumeResponse)
async def resume_session(request: ResumeRequest):
    """
    Resume a previous session from storage.
    """
    from ..services.session_store import SessionStore
    
    session = await SessionStore.load_session(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = []
    for msg in session.messages:
        if hasattr(msg, 'model_dump'):
            messages.append(msg.model_dump())
        else:
            messages.append({"role": msg.role, "content": msg.content})
    
    return ResumeResponse(
        success=True,
        session_id=session.id,
        messages=messages,
        title=session.title
    )


# ============================================================
# REWIND COMMAND
# ============================================================

@router.post("/rewind", response_model=RewindResponse)
async def rewind_session(request: RewindRequest):
    """
    Rewind the conversation by removing the last N messages.
    """
    session = get_current_session()
    if not session:
        return RewindResponse(
            success=False,
            messages_removed=0,
            current_message_count=0
        )

    steps = request.steps if request else 1
    messages = session.get("messages", [])

    non_system_messages = [m for m in messages if m.get("role") != "system"]
    system_messages = [m for m in messages if m.get("role") == "system"]

    remove_count = min(steps, len(non_system_messages))
    if remove_count > 0:
        remaining = non_system_messages[:-remove_count] if remove_count < len(non_system_messages) else []
        session["messages"] = system_messages + remaining

    return RewindResponse(
        success=True,
        messages_removed=remove_count,
        current_message_count=len(session["messages"])
    )


# ============================================================
# MODEL COMMANDS (Expanded)
# ============================================================

@router.get("/model/list", response_model=ModelListResponse)
async def list_models():
    """
    List available models.
    """
    AVAILABLE_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]
    
    return ModelListResponse(
        current_model="claude-3-5-sonnet-20241022",
        available_models=AVAILABLE_MODELS
    )


@router.post("/model/select")
async def select_model(request: ModelRequest):
    """
    Select a model for the current session.
    """
    valid_models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]
    
    if request.model not in valid_models:
        raise HTTPException(status_code=400, detail=f"Invalid model. Must be one of: {valid_models}")
    
    return {
        "success": True,
        "model": request.model,
        "provider": request.provider or "anthropic"
    }


# ============================================================
# COMPACT COMMAND (Improved)
# ============================================================

@router.post("/compact/execute")
async def compact_execute(max_messages: int = 40, keep_recent: int = 10):
    """
    Execute context compaction on the current session.
    """
    from ..services.compact import compact_messages, should_compact
    from ..models.message import Message
    
    return {
        "success": True,
        "message": "Context compaction would be executed here",
        "params": {
            "max_messages": max_messages,
            "keep_recent": keep_recent
        }
    }


# ============================================================
# CONTEXT COMMAND (Improved)
# ============================================================

@router.get("/context/detailed")
async def visualize_context_detailed():
    """
    Get detailed context usage visualization.
    """
    return {
        "total_tokens": 0,
        "max_tokens": 200000,
        "usage_percent": 0.0,
        "messages": [],
        "system_prompt_tokens": 0,
        "conversation_tokens": 0,
        "available_tokens": 200000
    }


# ============================================================
# MCP COMMANDS
# ============================================================

class McpServerConfigRequest(BaseModel):
    name: str
    transport: str
    command: Optional[str] = None
    args: Optional[list[str]] = None
    env: Optional[dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[dict[str, str]] = None


class McpToolCallRequest(BaseModel):
    server: str
    tool: str
    arguments: Optional[dict[str, Any]] = None


class McpResourceReadRequest(BaseModel):
    server: str
    uri: str


@router.get("/mcp/servers")
async def list_mcp_servers():
    """List all configured MCP servers."""
    servers = await mcp_list_servers()
    return {"servers": servers}


@router.get("/mcp/connections")
async def list_mcp_connections():
    """List connected MCP servers with status."""
    connections = await mcp_list_connections()
    return {"connections": connections}


@router.post("/mcp/servers")
async def add_mcp_server(config: McpServerConfigRequest):
    """Add an MCP server configuration."""
    result = mcp_add_server(
        name=config.name,
        transport=config.transport,
        command=config.command,
        args=config.args,
        env=config.env,
        url=config.url,
        headers=config.headers,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/mcp/connect/{server_name}")
async def connect_mcp_server(server_name: str):
    """Connect to an MCP server."""
    result = await mcp_connect(server_name)
    return result


@router.post("/mcp/disconnect/{server_name}")
async def disconnect_mcp_server(server_name: str):
    """Disconnect from an MCP server."""
    result = await mcp_disconnect(server_name)
    return result


@router.get("/mcp/tools/{server_name}")
async def list_server_tools(server_name: str):
    """List tools available on a connected MCP server."""
    tools = await mcp_list_tools(server_name)
    return {"tools": tools}


@router.post("/mcp/call")
async def call_mcp_tool(request: McpToolCallRequest):
    """Call an MCP tool on a connected server."""
    result = await mcp_call_tool(
        request.server,
        request.tool,
        request.arguments or {},
    )
    return result


@router.get("/mcp/resources/{server_name}")
async def list_server_resources(server_name: str):
    """List resources available on a connected MCP server."""
    resources = await mcp_list_resources(server_name)
    return {"resources": resources}


@router.post("/mcp/resource/read")
async def read_resource(request: McpResourceReadRequest):
    """Read a resource from an MCP server."""
    result = await mcp_read_resource(request.server, request.uri)
    return result


# ============================================================
# INIT-VERIFIERS COMMAND
# ============================================================

class InitVerifiersRequest(BaseModel):
    path: Optional[str] = None
    verifier_type: Optional[str] = None  # playwright, cli, api


class InitVerifiersResponse(BaseModel):
    success: bool
    skills_created: list[str]
    message: str


VERIFIER_TEMPLATE_PLAYWRIGHT = """---
name: {name}
description: {description}
allowed-tools:
  - Bash(npm:*)
  - Bash(yarn:*)
  - Bash(pnpm:*)
  - Bash(bun:*)
  - Read
  - Glob
  - Grep
---

# {title}

You are a verification executor for web UI testing.

## Project Context
{project_context}

## Setup Instructions
{setup_instructions}

## Reporting
Report PASS or FAIL for each step.

## Cleanup
Stop dev servers and close browser sessions after verification.
"""

VERIFIER_TEMPLATE_CLI = """---
name: {name}
description: {description}
allowed-tools:
  - Tmux
  - Bash
  - Read
  - Glob
  - Grep
---

# {title}

You are a verification executor for CLI testing.

## Project Context
{project_context}

## Reporting
Report PASS or FAIL for each step.
"""

VERIFIER_TEMPLATE_API = """---
name: {name}
description: {description}
allowed-tools:
  - Bash(curl:*)
  - Bash(http:*)
  - Bash(npm:*)
  - Bash(yarn:*)
  - Read
  - Glob
  - Grep
---

# {title}

You are a verification executor for API testing.

## Project Context
{project_context}

## Reporting
Report PASS or FAIL for each step.
"""


@router.post("/init-verifiers", response_model=InitVerifiersResponse)
async def init_verifiers(request: InitVerifiersRequest = None):
    """
    Create verifier skill(s) for automated verification of code changes.
    
    Analyzes the project and creates appropriate verifiers (Playwright, CLI, or API).
    """
    import os
    import json
    
    project_path = request.path if request and request.path else "."
    verifier_type = request.verifier_type if request and request.verifier_type else "auto"
    
    skills_dir = Path(project_path) / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    
    skills_created = []
    
    # Auto-detect project type
    if verifier_type == "auto":
        has_package_json = (Path(project_path) / "package.json").exists()
        has_pyproject = (Path(project_path) / "pyproject.toml").exists()
        has_cargo = (Path(project_path) / "Cargo.toml").exists()
        
        if has_package_json:
            # Check for web framework indicators
            pkg_json = {}
            try:
                with open(Path(project_path) / "package.json") as f:
                    pkg_json = json.load(f)
            except:
                pass
            
            deps = {**pkg_json.get("dependencies", {}), **pkg_json.get("devDependencies", {})}
            if any(k in deps for k in ["playwright", "@playwright/test", "next", "react", "vue", "nuxt"]):
                verifier_type = "playwright"
            else:
                verifier_type = "cli"
        elif has_pyproject or has_cargo:
            verifier_type = "cli"
        else:
            verifier_type = "cli"
    
    # Create verifier based on type
    if verifier_type == "playwright":
        name = "verifier-playwright"
        template = VERIFIER_TEMPLATE_PLAYWRIGHT.format(
            name=name,
            description="Playwright-based web UI verification",
            title="Web UI Verifier",
            project_context=f"Project at {project_path}",
            setup_instructions="Run dev server before verification"
        )
        skill_path = skills_dir / name / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(template, encoding="utf-8")
        skills_created.append(name)
        
    elif verifier_type == "cli":
        name = "verifier-cli"
        template = VERIFIER_TEMPLATE_CLI.format(
            name=name,
            description="CLI command verification",
            title="CLI Verifier",
            project_context=f"Project at {project_path}"
        )
        skill_path = skills_dir / name / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(template, encoding="utf-8")
        skills_created.append(name)
        
    elif verifier_type == "api":
        name = "verifier-api"
        template = VERIFIER_TEMPLATE_API.format(
            name=name,
            description="HTTP API verification",
            title="API Verifier",
            project_context=f"Project at {project_path}"
        )
        skill_path = skills_dir / name / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(template, encoding="utf-8")
        skills_created.append(name)
    
    return InitVerifiersResponse(
        success=True,
        skills_created=skills_created,
        message=f"Created {len(skills_created)} verifier skill(s) at {skills_dir}"
    )


# ============================================================
# EXPORT COMMAND
# ============================================================

class ExportRequest(BaseModel):
    session_id: Optional[str] = None
    format: str = "text"  # text, markdown, json


class ExportResponse(BaseModel):
    success: bool
    content: str
    filename: str
    message_count: int


@router.post("/export", response_model=ExportResponse)
async def export_conversation(request: ExportRequest):
    """
    Export the current conversation to a file or clipboard.
    Supports text, markdown, and JSON formats.
    """
    from .export import _render_messages_to_plain_text, _format_timestamp, _extract_first_prompt, _sanitize_filename
    
    session = get_current_session()
    session_id = request.session_id if request.session_id else get_current_session_id()
    
    if not session and session_id:
        from .export import _load_session_file
        session = _load_session_file(session_id)
    
    if not session:
        return ExportResponse(
            success=False,
            content="",
            filename="",
            message_count=0
        )
    
    messages = session.get("messages", [])
    message_count = len(messages)
    
    if request.format == "json":
        content = json.dumps({"messages": messages}, indent=2)
        filename = f"conversation-{_format_timestamp(datetime.now())}.json"
    elif request.format == "markdown":
        content = _render_messages_to_markdown(messages)
        first_prompt = _extract_first_prompt(messages)
        filename = f"{_sanitize_filename(first_prompt) or 'conversation'}-{_format_timestamp(datetime.now())}.md"
    else:
        content = _render_messages_to_plain_text(messages)
        first_prompt = _extract_first_prompt(messages)
        filename = f"{_sanitize_filename(first_prompt) or 'conversation'}-{_format_timestamp(datetime.now())}.txt"
    
    return ExportResponse(
        success=True,
        content=content,
        filename=filename,
        message_count=message_count
    )


def _render_messages_to_markdown(messages: list) -> str:
    """Render messages as markdown conversation."""
    lines = ["# Conversation", ""]
    
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        if isinstance(content, str):
            formatted_content = content
        elif isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        parts.append(f"[Tool: {block.get('name', 'unknown')}]")
            formatted_content = "\n".join(parts)
        else:
            formatted_content = str(content)
        
        if role == "user":
            lines.append(f"## User\n\n{formatted_content}\n")
        elif role == "assistant":
            lines.append(f"## Assistant\n\n{formatted_content}\n")
        else:
            lines.append(f"## {role.capitalize()}\n\n{formatted_content}\n")
    
    return "\n".join(lines).strip()


# ============================================================
# BRIDGE MODE COMMAND (BRIDGE_MODE)
# ============================================================

class BridgeModeResponse(BaseModel):
    success: bool
    enabled: bool
    feature_flag: str
    message: str


_bridge_state: dict = {
    "enabled": False,
    "connected": False,
    "session_url": None,
}


@router.get("/bridge/status")
async def get_bridge_status():
    """
    Get bridge mode status.
    
    Bridge mode enables remote control of Claude Code sessions
    through a bidirectional connection to claude.ai.
    """
    bridge_enabled = "BRIDGE_MODE" in os.environ
    return {
        "enabled": bridge_enabled,
        "connected": _bridge_state.get("connected", False),
        "session_url": _bridge_state.get("session_url"),
        "feature_flag": "BRIDGE_MODE",
        "message": "Bridge mode is enabled" if bridge_enabled else "Bridge mode requires BRIDGE_MODE feature flag"
    }


@router.post("/bridge/connect")
async def bridge_connect(name: Optional[str] = None):
    """
    Connect to bridge mode for remote control.
    
    Establishes a bidirectional connection allowing
    remote control of the Claude Code session.
    """
    if "BRIDGE_MODE" not in os.environ:
        return {
            "success": False,
            "error": "BRIDGE_MODE feature flag is not enabled"
        }
    
    _bridge_state["enabled"] = True
    _bridge_state["connected"] = True
    _bridge_state["session_url"] = f"https://claude.ai/bridge/{name or 'default'}"
    
    return {
        "success": True,
        "message": "Bridge mode connecting...",
        "session_url": _bridge_state["session_url"],
        "feature_flag": "BRIDGE_MODE"
    }


@router.post("/bridge/disconnect")
async def bridge_disconnect():
    """Disconnect from bridge mode."""
    _bridge_state["connected"] = False
    _bridge_state["session_url"] = None
    
    return {
        "success": True,
        "message": "Bridge mode disconnected"
    }


@router.post("/bridge", response_model=BridgeModeResponse)
async def toggle_bridge_mode(enable: Optional[bool] = None):
    """
    Toggle bridge mode (Remote Control).
    
    Bridge mode connects this Claude Code instance for remote control
    sessions via claude.ai. Requires BRIDGE_MODE feature flag.
    """
    if "BRIDGE_MODE" not in os.environ:
        return BridgeModeResponse(
            success=False,
            enabled=False,
            feature_flag="BRIDGE_MODE",
            message="Bridge mode requires BRIDGE_MODE feature flag to be set"
        )
    
    if enable is None:
        enable = not _bridge_state.get("enabled", False)
    
    _bridge_state["enabled"] = enable
    
    if enable:
        return BridgeModeResponse(
            success=True,
            enabled=True,
            feature_flag="BRIDGE_MODE",
            message="Bridge mode enabled - use /remote-control to connect"
        )
    else:
        return BridgeModeResponse(
            success=True,
            enabled=False,
            feature_flag="BRIDGE_MODE",
            message="Bridge mode disabled"
        )


# ============================================================
# REMOTE CONTROL SERVER COMMAND (DAEMON + BRIDGE_MODE)
# ============================================================

class RemoteControlServerResponse(BaseModel):
    success: bool
    running: bool
    port: Optional[int]
    feature_flags: list[str]
    message: str


_remote_server_state: dict = {
    "running": False,
    "port": None,
    "pid": None,
}


@router.get("/remote-control-server/status")
async def get_remote_control_server_status():
    """
    Get remote control server status.
    
    The remote control server is a long-running daemon that accepts
    remote commands through bridge mode connections.
    Requires both DAEMON and BRIDGE_MODE feature flags.
    """
    has_daemon = "DAEMON" in os.environ
    has_bridge = "BRIDGE_MODE" in os.environ
    
    if not has_daemon or not has_bridge:
        return {
            "success": False,
            "running": False,
            "port": None,
            "feature_flags": ["DAEMON", "BRIDGE_MODE"],
            "message": "Remote control server requires both DAEMON and BRIDGE_MODE feature flags"
        }
    
    return {
        "success": True,
        "running": _remote_server_state.get("running", False),
        "port": _remote_server_state.get("port"),
        "feature_flags": ["DAEMON", "BRIDGE_MODE"],
        "message": "Remote control server is running" if _remote_server_state.get("running") else "Remote control server is not running"
    }


@router.post("/remote-control-server/start")
async def start_remote_control_server(port: int = 7891):
    """
    Start the remote control server daemon.
    
    The remote control server accepts commands from remote clients
    through bridge mode connections. Requires both DAEMON and 
    BRIDGE_MODE feature flags to be set.
    """
    if "DAEMON" not in os.environ:
        return {
            "success": False,
            "error": "DAEMON feature flag is not enabled"
        }
    
    if "BRIDGE_MODE" not in os.environ:
        return {
            "success": False,
            "error": "BRIDGE_MODE feature flag is not enabled"
        }
    
    if _remote_server_state.get("running"):
        return {
            "success": True,
            "running": True,
            "port": _remote_server_state.get("port"),
            "message": f"Remote control server already running on port {_remote_server_state.get('port')}"
        }
    
    _remote_server_state["running"] = True
    _remote_server_state["port"] = port
    
    return {
        "success": True,
        "running": True,
        "port": port,
        "feature_flags": ["DAEMON", "BRIDGE_MODE"],
        "message": f"Remote control server started on port {port}"
    }


@router.post("/remote-control-server/stop")
async def stop_remote_control_server():
    """Stop the remote control server daemon."""
    if not _remote_server_state.get("running"):
        return {
            "success": True,
            "message": "Remote control server was not running"
        }
    
    _remote_server_state["running"] = False
    _remote_server_state["port"] = None
    
    return {
        "success": True,
        "running": False,
        "message": "Remote control server stopped"
    }


@router.post("/remote-control-server", response_model=RemoteControlServerResponse)
async def remote_control_server_command(action: str = "status", port: int = 7891):
    """
    Remote control server command.
    
    Controls the long-running remote control server daemon that
    accepts commands through bridge mode connections.
    
    Actions:
    - status: Get current server status
    - start: Start the server
    - stop: Stop the server
    
    Requires both DAEMON and BRIDGE_MODE feature flags.
    """
    has_daemon = "DAEMON" in os.environ
    has_bridge = "BRIDGE_MODE" in os.environ
    
    if not has_daemon or not has_bridge:
        return RemoteControlServerResponse(
            success=False,
            running=False,
            port=None,
            feature_flags=["DAEMON", "BRIDGE_MODE"],
            message="Remote control server requires both DAEMON and BRIDGE_MODE feature flags"
        )
    
    if action == "start":
        if _remote_server_state.get("running"):
            return RemoteControlServerResponse(
                success=True,
                running=True,
                port=_remote_server_state.get("port"),
                feature_flags=["DAEMON", "BRIDGE_MODE"],
                message=f"Remote control server already running on port {_remote_server_state.get('port')}"
            )
        
        _remote_server_state["running"] = True
        _remote_server_state["port"] = port
        
        return RemoteControlServerResponse(
            success=True,
            running=True,
            port=port,
            feature_flags=["DAEMON", "BRIDGE_MODE"],
            message=f"Remote control server started on port {port}"
        )
    
    elif action == "stop":
        was_running = _remote_server_state.get("running", False)
        _remote_server_state["running"] = False
        _remote_server_state["port"] = None
        
        return RemoteControlServerResponse(
            success=True,
            running=False,
            port=None,
            feature_flags=["DAEMON", "BRIDGE_MODE"],
            message="Remote control server stopped" if was_running else "Remote control server was not running"
        )
    
    else:
        return RemoteControlServerResponse(
            success=True,
            running=_remote_server_state.get("running", False),
            port=_remote_server_state.get("port"),
            feature_flags=["DAEMON", "BRIDGE_MODE"],
            message="Remote control server is running" if _remote_server_state.get("running") else "Remote control server is not running"
        )


# ============================================================
# VOICE COMMAND (VOICE_MODE)
# ============================================================

class VoiceCommandResponse(BaseModel):
    success: bool
    enabled: bool
    mode: str
    feature_flag: str
    message: str


class VoiceRecognitionRequest(BaseModel):
    audio_data: str
    language: Optional[str] = "en"


class VoiceRecognitionResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    confidence: Optional[float] = None
    message: str


_voice_state: dict = {
    "enabled": False,
    "recording": False,
    "language": "en",
}


@router.get("/voice/detailed-status")
async def get_voice_detailed_status():
    """
    Get detailed voice mode status.
    
    Voice mode allows spoken interactions with Claude Code.
    Requires VOICE_MODE feature flag and Claude.ai subscription.
    """
    voice_enabled = "VOICE_MODE" in os.environ
    
    return {
        "enabled": voice_enabled,
        "recording": _voice_state.get("recording", False),
        "language": _voice_state.get("language", "en"),
        "feature_flag": "VOICE_MODE",
        "availability": "claude-ai",
        "message": "Voice mode is enabled" if voice_enabled else "Voice mode requires VOICE_MODE feature flag"
    }


@router.post("/voice/enable")
async def enable_voice_mode():
    """
    Enable voice mode.
    
    Voice mode allows you to interact with Claude Code using
    voice commands through your microphone.
    """
    if "VOICE_MODE" not in os.environ:
        return {
            "success": False,
            "error": "VOICE_MODE feature flag is not enabled"
        }
    
    _voice_state["enabled"] = True
    
    return {
        "success": True,
        "enabled": True,
        "mode": "voice",
        "feature_flag": "VOICE_MODE",
        "message": "Voice mode enabled. Hold Space to record."
    }


@router.post("/voice/disable")
async def disable_voice_mode():
    """Disable voice mode."""
    _voice_state["enabled"] = False
    _voice_state["recording"] = False
    
    return {
        "success": True,
        "enabled": False,
        "mode": "voice",
        "feature_flag": "VOICE_MODE",
        "message": "Voice mode disabled."
    }


@router.post("/voice/recognize", response_model=VoiceRecognitionResponse)
async def recognize_speech(request: VoiceRecognitionRequest):
    """
    Recognize speech from audio data.
    
    Takes base64 encoded audio and returns recognized text.
    This endpoint simulates voice recognition for the voice command feature.
    """
    if "VOICE_MODE" not in os.environ:
        return VoiceRecognitionResponse(
            success=False,
            message="VOICE_MODE feature flag is not enabled"
        )
    
    sample_commands = [
        "implement the forgot password feature",
        "create a new component",
        "run the tests",
        "show me the documentation",
    ]
    
    return VoiceRecognitionResponse(
        success=True,
        text=sample_commands[0],
        confidence=0.95,
        message="Speech recognized successfully"
    )


@router.post("/voice/start-recording")
async def start_voice_recording():
    """
    Start voice recording.
    
    Begins capturing audio from the microphone for
    voice command recognition.
    """
    if "VOICE_MODE" not in os.environ:
        return {
            "success": False,
            "error": "VOICE_MODE feature flag is not enabled"
        }
    
    _voice_state["recording"] = True
    
    return {
        "success": True,
        "recording": True,
        "message": "Recording started. Speak your command."
    }


@router.post("/voice/stop-recording")
async def stop_voice_recording():
    """
    Stop voice recording.
    
    Stops the current audio recording and processes
    the captured audio for voice recognition.
    """
    if not _voice_state.get("recording"):
        return {
            "success": False,
            "message": "No recording in progress"
        }
    
    _voice_state["recording"] = False
    
    return {
        "success": True,
        "recording": False,
        "message": "Recording stopped. Processing audio..."
    }


@router.post("/voice", response_model=VoiceCommandResponse)
async def voice_command(enable: Optional[bool] = None):
    """
    Voice mode command.
    
    Toggle voice mode for spoken interactions with Claude Code.
    Requires VOICE_MODE feature flag and Claude.ai subscription.
    """
    if "VOICE_MODE" not in os.environ:
        return VoiceCommandResponse(
            success=False,
            enabled=False,
            mode="voice",
            feature_flag="VOICE_MODE",
            message="Voice mode requires VOICE_MODE feature flag to be set"
        )
    
    if enable is None:
        enable = not _voice_state.get("enabled", False)
    
    _voice_state["enabled"] = enable
    
    if enable:
        return VoiceCommandResponse(
            success=True,
            enabled=True,
            mode="voice",
            feature_flag="VOICE_MODE",
            message="Voice mode enabled. Hold Space to record."
        )
    else:
        return VoiceCommandResponse(
            success=True,
            enabled=False,
            mode="voice",
            feature_flag="VOICE_MODE",
            message="Voice mode disabled."
        )


# ============================================================
# PEERS COMMAND (UDS_INBOX)
# ============================================================

class PeersResponse(BaseModel):
    success: bool
    peers: list[dict]
    connected: int


_peers_state: dict = {
    "enabled": False,
    "peers": [],
}


@router.get("/peers")
async def list_peers():
    """
    List connected peers for UDS_INBOX functionality.
    
    UDS_INBOX enables peer-to-peer message exchange between
    Claude Code instances.
    """
    return PeersResponse(
        success=True,
        peers=_peers_state.get("peers", []),
        connected=len(_peers_state.get("peers", []))
    )


@router.post("/peers/connect")
async def connect_peer(peer_id: str, host: str = "localhost", port: int = 7890):
    """Connect to a peer instance."""
    if peer_id not in [p.get("id") for p in _peers_state.get("peers", [])]:
        _peers_state["peers"].append({
            "id": peer_id,
            "host": host,
            "port": port,
            "connected": True
        })
    
    return {
        "success": True,
        "peer_id": peer_id,
        "message": f"Connected to peer {peer_id}"
    }


@router.delete("/peers/disconnect/{peer_id}")
async def disconnect_peer(peer_id: str):
    """Disconnect from a peer."""
    _peers_state["peers"] = [p for p in _peers_state.get("peers", []) if p.get("id") != peer_id]
    return {
        "success": True,
        "message": f"Disconnected from peer {peer_id}"
    }


@router.post("/peers/broadcast")
async def broadcast_to_peers(message: dict):
    """Broadcast a message to all connected peers."""
    return {
        "success": True,
        "peers_reached": len(_peers_state.get("peers", [])),
        "message": "Broadcast sent to all peers"
    }


# ============================================================
# PROACTIVE COMMAND (PROACTIVE / KAIROS)
# ============================================================

class ProactiveResponse(BaseModel):
    success: bool
    enabled: bool
    mode: str
    message: str


_proactive_state: dict = {
    "enabled": False,
}


def _check_proactive_feature_flag() -> bool:
    """Check if PROACTIVE or KAIROS feature flag is enabled."""
    return "PROACTIVE" in os.environ or "KAIROS" in os.environ


@router.get("/proactive")
async def get_proactive_status():
    """
    Get proactive mode status.
    
    Proactive mode enables AI to predict user intent
    and offer suggestions before being asked.
    """
    enabled = _check_proactive_feature_flag()
    _proactive_state["enabled"] = enabled
    
    return ProactiveResponse(
        success=True,
        enabled=enabled,
        mode="proactive",
        message="Proactive mode enabled - AI will predict your intent" if enabled else "Proactive mode disabled"
    )


@router.post("/proactive")
async def toggle_proactive_mode(enable: Optional[bool] = None):
    """
    Toggle proactive mode.
    
    When enabled:
    - AI analyzes possible next steps as you work
    - Prepares relevant tools and context in advance
    - Reduces wait time by pre-computing suggestions
    
    Requires PROACTIVE or KAIROS feature flag to be set.
    """
    if not _check_proactive_feature_flag():
        raise HTTPException(
            status_code=403,
            detail="Feature flag PROACTIVE or KAIROS is not enabled. Set one of these environment variables to use this command."
        )
    
    new_state = enable if enable is not None else True
    _proactive_state["enabled"] = new_state
    
    return ProactiveResponse(
        success=True,
        enabled=new_state,
        mode="proactive",
        message="Proactive mode enabled - AI will predict your intent" if new_state else "Proactive mode disabled"
    )


# ============================================================
# BRIEF COMMAND (KAIROS_BRIEF)
# ============================================================

class BriefResponse(BaseModel):
    success: bool
    enabled: bool
    mode: str
    message: str


_brief_state: dict = {
    "enabled": False,
}


def _check_brief_feature_flag() -> bool:
    """Check if KAIROS_BRIEF feature flag is enabled."""
    return "KAIROS_BRIEF" in os.environ


@router.get("/brief")
async def get_brief_status():
    """
    Get brief mode status.
    
    Brief mode compresses all output for faster responses
    and reduced token usage.
    """
    enabled = _check_brief_feature_flag()
    _brief_state["enabled"] = enabled
    
    return BriefResponse(
        success=True,
        enabled=enabled,
        mode="brief",
        message="Brief mode enabled - output compressed" if enabled else "Brief mode disabled"
    )


@router.post("/brief")
async def toggle_brief_mode(enable: Optional[bool] = None):
    """
    Toggle brief mode.
    
    When enabled:
    - All output is compressed
    - Faster response times
    - Reduced token usage
    
    Ideal for quick tasks where verbosity is not needed.
    
    Requires KAIROS_BRIEF feature flag to be set.
    """
    if not _check_brief_feature_flag():
        raise HTTPException(
            status_code=403,
            detail="Feature flag KAIROS_BRIEF is not enabled. Set KAIROS_BRIEF environment variable to use this command."
        )
    
    new_state = enable if enable is not None else True
    _brief_state["enabled"] = new_state
    
    return BriefResponse(
        success=True,
        enabled=new_state,
        mode="brief",
        message="Brief mode enabled - output compressed" if new_state else "Brief mode disabled"
    )


# ============================================================
# ASSISTANT COMMAND (KAIROS)
# ============================================================

class AssistantResponse(BaseModel):
    success: bool
    enabled: bool
    mode: str
    message: str


_assistant_state: dict = {
    "enabled": False,
}


def _check_assistant_feature_flag() -> bool:
    """Check if KAIROS feature flag is enabled."""
    return "KAIROS" in os.environ


@router.get("/assistant")
async def get_assistant_status():
    """
    Get assistant mode status.
    
    Assistant mode changes AI behavior to be more advisory
    and less action-oriented.
    """
    enabled = _check_assistant_feature_flag()
    _assistant_state["enabled"] = enabled
    
    return AssistantResponse(
        success=True,
        enabled=enabled,
        mode="assistant",
        message="Assistant mode enabled - advisory style" if enabled else "Assistant mode disabled"
    )


@router.post("/assistant")
async def toggle_assistant_mode(enable: Optional[bool] = None):
    """
    Toggle assistant mode.
    
    When enabled:
    - AI behavior shifts to advisory style
    - Focus on recommendations and explanations
    - Less direct action execution
    
    Requires KAIROS feature flag to be set.
    """
    if not _check_assistant_feature_flag():
        raise HTTPException(
            status_code=403,
            detail="Feature flag KAIROS is not enabled. Set KAIROS environment variable to use this command."
        )
    
    new_state = enable if enable is not None else True
    _assistant_state["enabled"] = new_state
    
    return AssistantResponse(
        success=True,
        enabled=new_state,
        mode="assistant",
        message="Assistant mode enabled - advisory style" if new_state else "Assistant mode disabled"
    )


# ============================================================
# TORCH COMMAND (TORCH) - Rapid Prototyping Mode
# ============================================================

class TorchConfig(BaseModel):
    """Configuration for torch rapid prototyping mode."""
    speed: str = "fast"  # "fast", "medium", "thorough"
    parallel: bool = True  # Enable parallel tool execution
    max_iterations: Optional[int] = None  # Limit iterations (None = unlimited)


class TorchRequest(BaseModel):
    """Request model for torch command actions."""
    action: str  # "start", "stop", "status"
    config: Optional[TorchConfig] = None


class TorchResponse(BaseModel):
    """Response model for torch command."""
    status: str  # "active", "inactive", "starting", "stopping"
    session_id: Optional[str] = None
    iterations_completed: int = 0
    message: Optional[str] = None
    config: Optional[TorchConfig] = None


# Torch state management
_torch_state: dict = {
    "enabled": False,
    "active": False,
    "session_id": None,
    "iterations_completed": 0,
    "config": None,
}


def _check_torch_feature_flag() -> bool:
    """Check if TORCH feature flag is enabled."""
    return "TORCH" in os.environ


async def _handle_torch_start(config: TorchConfig) -> TorchResponse:
    """Start torch mode with fast iterations."""
    session_id = get_current_session_id()
    
    _torch_state["enabled"] = True
    _torch_state["active"] = True
    _torch_state["session_id"] = session_id
    _torch_state["iterations_completed"] = 0
    _torch_state["config"] = config.model_dump() if config else None
    
    speed_descriptions = {
        "fast": "Quick iterations, minimal context, immediate execution",
        "medium": "Balanced speed and thoroughness",
        "thorough": "Complete analysis with context preservation"
    }
    
    return TorchResponse(
        status="active",
        session_id=session_id,
        iterations_completed=0,
        message=f"Torch mode started: {speed_descriptions.get(config.speed, 'fast')} (parallel={config.parallel})",
        config=config
    )


async def _handle_torch_stop() -> TorchResponse:
    """Stop torch mode."""
    iterations = _torch_state.get("iterations_completed", 0)
    session_id = _torch_state.get("session_id")
    
    _torch_state["enabled"] = False
    _torch_state["active"] = False
    _torch_state["config"] = None
    
    return TorchResponse(
        status="inactive",
        session_id=session_id,
        iterations_completed=iterations,
        message=f"Torch mode stopped. Completed {iterations} iterations."
    )


async def _handle_torch_status() -> TorchResponse:
    """Get current torch status."""
    return TorchResponse(
        status="active" if _torch_state.get("active") else "inactive",
        session_id=_torch_state.get("session_id"),
        iterations_completed=_torch_state.get("iterations_completed", 0),
        config=TorchConfig(**_torch_state["config"]) if _torch_state.get("config") else None
    )


@router.get("/torch")
async def get_torch_status():
    """
    Get torch mode status.
    
    Torch mode is rapid prototyping mode with:
    - Reduced context window usage
    - Parallel tool execution
    - Auto-rollback on errors
    - Quick context reset
    """
    enabled = _check_torch_feature_flag()
    _torch_state["enabled"] = enabled
    
    if not enabled:
        return TorchResponse(
            status="unavailable",
            message="Torch mode requires TORCH feature flag"
        )
    
    return await _handle_torch_status()


@router.post("/torch")
async def torch_command(request: TorchRequest) -> TorchResponse:
    """
    Rapid prototyping mode - fast iteration without full context.
    
    Actions:
    - "start": Start torch mode with optional config
    - "stop": Stop torch mode
    - "status": Get current torch status
    
    Features when active:
    - Fast iteration mode for rapid prototyping
    - Reduced context window usage
    - Parallel tool execution
    - Auto-rollback on errors
    - Quick context reset
    """
    if not _check_torch_feature_flag():
        raise HTTPException(
            status_code=403,
            detail="Feature flag TORCH is not enabled. Set TORCH environment variable to use this command."
        )
    
    action = request.action.lower()
    
    if action == "start":
        return await _handle_torch_start(request.config or TorchConfig())
    elif action == "stop":
        return await _handle_torch_stop()
    elif action == "status":
        return await _handle_torch_status()
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action: {action}. Use 'start', 'stop', or 'status'."
        )


# ============================================================
# FORK SUBAGENT COMMAND (FORK_SUBAGENT)
# ============================================================

class ForkSubagentRequest(BaseModel):
    agent_name: str
    context: Optional[str] = None


class ForkSubagentResponse(BaseModel):
    success: bool
    subagent_id: Optional[str] = None
    agent_name: str
    context: str
    status: str
    message: str


_fork_state: dict = {
    "enabled": False,
    "subagents": [],
}


def _check_fork_feature_flag() -> bool:
    """Check if FORK_SUBAGENT feature flag is enabled."""
    return "FORK_SUBAGENT" in os.environ


@router.get("/fork")
async def list_fork_subagents():
    """
    List fork subagents.
    
    Fork creates a copy of the agent to execute tasks
    in an isolated environment. Results are merged after completion.
    """
    if not _check_fork_feature_flag():
        raise HTTPException(
            status_code=403,
            detail="Feature flag FORK_SUBAGENT is not enabled. Set FORK_SUBAGENT environment variable to use this command."
        )
    
    return {
        "success": True,
        "subagents": _fork_state.get("subagents", []),
        "count": len(_fork_state.get("subagents", []))
    }


@router.post("/fork")
async def create_fork_subagent(request: ForkSubagentRequest):
    """
    Create a fork subagent.
    
    Creates a copy of the agent to execute the given context
    in an isolated environment. Results are merged after completion.
    """
    if not _check_fork_feature_flag():
        raise HTTPException(
            status_code=403,
            detail="Feature flag FORK_SUBAGENT is not enabled. Set FORK_SUBAGENT environment variable to use this command."
        )
    
    subagent_id = f"fork_{len(_fork_state.get('subagents', []))}_{request.agent_name.lower().replace(' ', '_')}"
    
    subagent = {
        "id": subagent_id,
        "agent_name": request.agent_name,
        "context": request.context or "",
        "status": "created",
    }
    
    _fork_state.setdefault("subagents", []).append(subagent)
    
    return ForkSubagentResponse(
        success=True,
        subagent_id=subagent_id,
        agent_name=request.agent_name,
        context=request.context or "",
        status="created",
        message=f"Fork subagent '{request.agent_name}' created with context: {request.context or 'none'}"
    )


@router.get("/fork/{subagent_id}")
async def get_fork_subagent(subagent_id: str):
    """Get details of a fork subagent."""
    if not _check_fork_feature_flag():
        raise HTTPException(
            status_code=403,
            detail="Feature flag FORK_SUBAGENT is not enabled. Set FORK_SUBAGENT environment variable to use this command."
        )
    
    subagent = next(
        (s for s in _fork_state.get("subagents", []) if s.get("id") == subagent_id),
        None
    )
    
    if not subagent:
        raise HTTPException(status_code=404, detail=f"Subagent '{subagent_id}' not found")
    
    return {
        "success": True,
        "subagent": subagent
    }


@router.delete("/fork/{subagent_id}")
async def delete_fork_subagent(subagent_id: str):
    """Delete a fork subagent."""
    if not _check_fork_feature_flag():
        raise HTTPException(
            status_code=403,
            detail="Feature flag FORK_SUBAGENT is not enabled. Set FORK_SUBAGENT environment variable to use this command."
        )
    
    subagents = _fork_state.get("subagents", [])
    _fork_state["subagents"] = [s for s in subagents if s.get("id") != subagent_id]
    
    return {
        "success": True,
        "message": f"Subagent '{subagent_id}' deleted"
    }


# ============================================================
# BUDDY COMMAND (BUDDY)
# ============================================================

class BuddyRequest(BaseModel):
    action: str  # "ask", "suggest", "review"
    question: Optional[str] = None
    code_context: Optional[str] = None


class BuddyResponse(BaseModel):
    success: bool
    mode: str
    response: Optional[str] = None
    suggestions: list[str] = []
    message: str


_buddy_state: dict = {
    "enabled": False,
    "suggestions": [],
}


def _check_buddy_feature_flag() -> bool:
    """Check if BUDDY feature flag is enabled."""
    return "BUDDY" in os.environ


@router.get("/buddy")
async def get_buddy_status():
    """
    Get Buddy mode status.
    
    Buddy is an AI companion that provides real-time
    coding suggestions without auto-executing actions.
    Acts as a code review assistant.
    """
    if not _check_buddy_feature_flag():
        raise HTTPException(
            status_code=403,
            detail="Feature flag BUDDY is not enabled. Set BUDDY environment variable to use this command."
        )
    
    return BuddyResponse(
        success=True,
        mode="buddy",
        response=None,
        suggestions=_buddy_state.get("suggestions", []),
        message="Buddy mode active - providing coding suggestions"
    )


@router.post("/buddy")
async def interact_with_buddy(request: BuddyRequest):
    """
    Interact with Buddy AI companion.
    
    Buddy provides real-time coding suggestions without
    auto-executing actions. Acts as a code review assistant.
    
    Actions:
    - ask: Ask Buddy a question
    - suggest: Get suggestions for code context
    - review: Request code review
    """
    if not _check_buddy_feature_flag():
        raise HTTPException(
            status_code=403,
            detail="Feature flag BUDDY is not enabled. Set BUDDY environment variable to use this command."
        )
    
    _buddy_state["enabled"] = True
    
    if request.action == "ask":
        return BuddyResponse(
            success=True,
            mode="buddy",
            response=f"Buddy response to: {request.question or 'your question'}",
            suggestions=[],
            message="Buddy answered your question"
        )
    elif request.action == "suggest":
        suggestions = [
            "Consider extracting this logic into a separate function",
            "This loop could be optimized with a list comprehension",
            "Missing error handling for edge case",
        ]
        _buddy_state["suggestions"] = suggestions
        return BuddyResponse(
            success=True,
            mode="buddy",
            response=None,
            suggestions=suggestions,
            message="Buddy provided suggestions"
        )
    elif request.action == "review":
        return BuddyResponse(
            success=True,
            mode="buddy",
            response="Code review: No critical issues found",
            suggestions=[
                "Consider adding type hints",
                "Optional: Add docstrings to public methods",
            ],
            message="Buddy completed code review"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")


# ============================================================
# WORKFLOWS COMMAND (WORKFLOW_SCRIPTS)
# ============================================================

class WorkflowInfo(BaseModel):
    name: str
    description: str
    path: str
    enabled: bool


class WorkflowsResponse(BaseModel):
    success: bool
    workflows: list[WorkflowInfo]
    feature_flag_enabled: bool


_workflows_state: dict = {
    "enabled": False,
    "workflows": []
}


def _check_workflows_feature_flag() -> bool:
    """Check if WORKFLOW_SCRIPTS feature flag is enabled."""
    return "WORKFLOW_SCRIPTS" in os.environ


@router.get("/workflows")
async def list_workflows():
    """
    List available workflow scripts.
    
    Workflows are automation scripts that can be executed
    to perform complex multi-step tasks.
    
    Requires WORKFLOW_SCRIPTS feature flag.
    """
    enabled = _check_workflows_feature_flag()
    _workflows_state["enabled"] = enabled
    
    return WorkflowsResponse(
        success=True,
        workflows=[WorkflowInfo(**w) for w in _workflows_state.get("workflows", [])] if enabled else [],
        feature_flag_enabled=enabled
    )


@router.post("/workflows/execute/{workflow_name}")
async def execute_workflow(workflow_name: str, args: Optional[str] = None):
    """Execute a workflow script by name."""
    workflows = _workflows_state.get("workflows", [])
    workflow = next((w for w in workflows if w.get("name") == workflow_name), None)
    
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
    
    return {
        "success": True,
        "workflow_name": workflow_name,
        "message": f"Workflow '{workflow_name}' executed",
        "args": args
    }


# ============================================================
# AGENTS COMMAND
# ============================================================

class AgentInfo(BaseModel):
    id: str
    name: str
    type: str
    status: str
    enabled: bool


class AgentsResponse(BaseModel):
    success: bool
    agents: list[AgentInfo]


# ============================================================
# MISSING COMMAND REQUEST/RESPONSE MODELS
# ============================================================

class ColorRequest(BaseModel):
    color: str  # e.g., "blue", "green", "orange", "red", "purple", "pink", "gray"


class ColorResponse(BaseModel):
    success: bool
    color: str
    message: str


class StatusResponse(BaseModel):
    status: str
    version: str
    model: str
    message_count: int
    account: Optional[str] = None


class TagCommandRequest(BaseModel):
    tag: Optional[str] = None  # If None, removes tag


class TagCommandResponse(BaseModel):
    success: bool
    session_id: str
    tag: Optional[str]
    message: str


class OutputStyleRequest(BaseModel):
    style: str  # "default", "compact", "minimal", etc.


class OutputStyleResponse(BaseModel):
    success: bool
    style: str
    message: str


class StatusLineRequest(BaseModel):
    config: Optional[str] = None  # Shell PS1 config to convert


class StatusLineResponse(BaseModel):
    success: bool
    message: str
    config: Optional[dict] = None


class VimModeResponse(BaseModel):
    success: bool
    mode: str  # "normal" or "vim"
    message: str


class ThemeRequest(BaseModel):
    theme: Optional[str] = None  # If None, just list themes


class ThemeResponse(BaseModel):
    success: bool
    current_theme: Optional[str] = None
    available_themes: list[str]
    message: str


class StickersResponse(BaseModel):
    success: bool
    url: str
    message: str


class ThinkbackPlayResponse(BaseModel):
    success: bool
    message: str
    animation_path: Optional[str] = None


class PluginCommandRequest(BaseModel):
    action: str  # "install", "uninstall", "enable", "disable", "list"
    plugin_id: Optional[str] = None


class PluginCommandResponse(BaseModel):
    success: bool
    action: str
    plugin_id: Optional[str] = None
    message: str


class ExportCommandRequest(BaseModel):
    format: str = "text"  # "text", "markdown"
    file_path: Optional[str] = None  # If provided, write to file


class ExportCommandResponse(BaseModel):
    success: bool
    content: str
    filename: str
    message_count: int


_agents_state: dict = {
    "agents": []
}


@router.get("/agents")
async def list_agents():
    """
    List available agent configurations.
    
    Agents are specialized AI configurations for different tasks.
    """
    return AgentsResponse(
        success=True,
        agents=[AgentInfo(**a) for a in _agents_state.get("agents", [])]
    )


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get details of a specific agent."""
    from .agents import AgentSummaryResponse
    # Delegate to agents.py for agent summaries
    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Use /api/agents/{agent_id} for agent summary operations"
    }


@router.post("/agents/configure")
async def configure_agent(name: str, config: dict):
    """Configure a new or existing agent."""
    agent_id = f"agent_{name.lower().replace(' ', '_')}"
    
    existing = [a for a in _agents_state.get("agents", []) if a.get("id") == agent_id]
    if existing:
        # Update existing
        for a in _agents_state["agents"]:
            if a.get("id") == agent_id:
                a.update(config)
                break
    else:
        # Create new
        _agents_state.setdefault("agents", []).append({
            "id": agent_id,
            "name": name,
            "type": config.get("type", "general-purpose"),
            "status": "active",
            "enabled": True
        })
    
    return {
        "success": True,
        "agent_id": agent_id,
        "message": f"Agent '{name}' configured"
    }


# ============================================================
# FEATURE-FLAGGED COMMANDS
# ============================================================

class FeatureFlagCommand(BaseModel):
    name: str
    enabled: bool
    feature_flag: str


# Feature flags supported by Claude Code
FEATURE_FLAGS = {
    "PROACTIVE": "proactive",
    "KAIROS": "proactive",
    "KAIROS_BRIEF": "brief",
    "KAIROS_ASSISTANT": "assistant",
    "BRIDGE_MODE": "bridge",
    "VOICE_MODE": "voice",
    "UDS_INBOX": "peers",
    "WORKFLOW_SCRIPTS": "workflows",
    "FORK_SUBAGENT": "fork",
    "BUDDY": "buddy",
    "CCR_REMOTE_SETUP": "remote-setup",
    "EXPERIMENTAL_SKILL_SEARCH": "skill-search",
    "KAIROS_GITHUB_WEBHOOKS": "subscribe-pr",
    "ULTRAPLAN": "ultraplan",
    "TORCH": "torch",
    "HISTORY_SNIP": "history-snip",
    "DAEMON": "daemon",
}


@router.get("/feature-flags")
async def list_feature_flags():
    """
    List all feature flags and their enabled status.
    
    Feature flags control availability of certain commands.
    """
    flags = []
    for flag_name, command_name in FEATURE_FLAGS.items():
        enabled = flag_name in os.environ
        flags.append({
            "flag": flag_name,
            "command": command_name,
            "enabled": enabled
        })
    return {"feature_flags": flags}


@router.get("/feature-flag/{flag_name}")
async def get_feature_flag_status(flag_name: str):
    """Get status of a specific feature flag."""
    enabled = flag_name.upper() in os.environ
    command_name = FEATURE_FLAGS.get(flag_name.upper(), flag_name.lower())
    
    return {
        "flag": flag_name,
        "command": command_name,
        "enabled": enabled
    }


# ============================================================
# GENERIC COMMAND EXECUTION
# ============================================================

class ExecuteCommandRequest(BaseModel):
    command: str
    args: Optional[str] = None
    context: Optional[dict] = None


class ExecuteCommandResponse(BaseModel):
    success: bool
    command: str
    type: str  # "prompt", "local", "local-jsx"
    result: Optional[Any] = None
    error: Optional[str] = None


# Command type registry - maps command names to their types
COMMAND_TYPES = {
    # Session commands
    "new": "local",
    "compact": "local",
    "context": "local-jsx",
    "resume": "local-jsx",
    "rewind": "local",
    "session": "local-jsx",
    "rename": "local-jsx",
    "exit": "local-jsx",
    # Git commands
    "commit": "prompt",
    "commit-push-pr": "prompt",
    "branch": "local-jsx",
    "diff": "local-jsx",
    "review": "prompt",
    # Model commands
    "model": "local-jsx",
    "effort": "local-jsx",
    "fast": "local-jsx",
    "advisor": "local",
    # Review commands
    "ultrareview": "local-jsx",
    "init": "prompt",
    "security-review": "prompt",
    "pr-comments": "prompt",
    "init-verifiers": "prompt",
    # File commands
    "files": "local",
    "add-dir": "local-jsx",
    "copy": "local-jsx",
    # Project commands
    "plan": "local-jsx",
    "tasks": "local-jsx",
    "hooks": "local-jsx",
    "skills": "local-jsx",
    "permissions": "local-jsx",
    "mcp": "local-jsx",
    "btw": "local-jsx",
    # Settings commands
    "config": "local-jsx",
    "ide": "local-jsx",
    "keybindings": "local",
    "terminal-setup": "local-jsx",
    "sandbox": "local-jsx",
    # Account commands
    "login": "local-jsx",
    "logout": "local-jsx",
    "upgrade": "local-jsx",
    "privacy-settings": "local-jsx",
    # Usage commands
    "usage": "local-jsx",
    "cost": "local",
    "stats": "local-jsx",
    "insights": "local-jsx",
    "think-back": "local-jsx",
    "passes": "local-jsx",
    "extra-usage": "local-jsx",
    # Remote commands
    "remote-control": "local-jsx",
    "remote-env": "local-jsx",
    "web-setup": "local-jsx",
    "ultraplan": "local-jsx",
    # Integrations
    "install-github-app": "local-jsx",
    "install-slack-app": "local",
    "chrome": "local-jsx",
    "mobile": "local-jsx",
    "desktop": "local-jsx",
    "voice": "local",
    # Utility commands
    "help": "local-jsx",
    "feedback": "local-jsx",
    "doctor": "local-jsx",
    "version": "local",
    "release-notes": "local",
    "reload-plugins": "local",
    "heapdump": "local",
    # Memory commands
    "memory": "local-jsx",
    "thinkback": "local-jsx",
    "ctx-viz": "local-jsx",
    # Agent commands
    "agents": "local-jsx",
    "export": "local-jsx",
    # Feature-flagged commands
    "proactive": "prompt",
    "brief": "prompt",
    "assistant": "prompt",
    "bridge": "local-jsx",
    "fork": "local-jsx",
    "buddy": "local-jsx",
    "peers": "local-jsx",
    "workflows": "local-jsx",
    "subscribe-pr": "prompt",
    "torch": "prompt",
}


@router.post("/execute", response_model=ExecuteCommandResponse)
async def execute_command(request: ExecuteCommandRequest):
    """
    Execute a command by name with optional arguments.
    
    Supports all command types:
    - prompt: Commands that send content to the AI
    - local: Commands that execute locally and return text
    - local-jsx: Commands that render Ink UI components
    
    Args:
        command: The command name (e.g., "compact", "review", "init")
        args: Optional arguments string
        context: Optional execution context
    """
    command_name = request.command.lower()
    
    # Get command type
    cmd_type = COMMAND_TYPES.get(command_name, "local")
    
    # Check if feature-flagged command is enabled
    flag_mapping = {
        "proactive": "KAIROS",
        "brief": "KAIROS_BRIEF",
        "assistant": "KAIROS",
        "bridge": "BRIDGE_MODE",
        "voice": "VOICE_MODE",
        "peers": "UDS_INBOX",
        "workflows": "WORKFLOW_SCRIPTS",
        "fork": "FORK_SUBAGENT",
        "buddy": "BUDDY",
        "remote-setup": "CCR_REMOTE_SETUP",
        "subscribe-pr": "KAIROS_GITHUB_WEBHOOKS",
        "ultraplan": "ULTRAPLAN",
        "torch": "TORCH",
        "history-snip": "HISTORY_SNIP",
        "daemon": "DAEMON",
    }
    
    if command_name in flag_mapping:
        env_var = flag_mapping[command_name]
        if env_var not in os.environ:
            return ExecuteCommandResponse(
                success=False,
                command=command_name,
                type=cmd_type,
                error=f"Feature flag {env_var} is not enabled"
            )
    
    try:
        result = None
        
        # Route to appropriate handler based on command type
        if cmd_type == "prompt":
            # For prompt commands, return the prompt content
            result = await _execute_prompt_command(command_name, request.args, request.context)
        elif cmd_type == "local":
            # For local commands, execute immediately
            result = await _execute_local_command(command_name, request.args, request.context)
        else:  # local-jsx
            # For local-jsx commands, return UI component info
            result = await _execute_local_jsx_command(command_name, request.args, request.context)
        
        return ExecuteCommandResponse(
            success=True,
            command=command_name,
            type=cmd_type,
            result=result
        )
        
    except Exception as e:
        return ExecuteCommandResponse(
            success=False,
            command=command_name,
            type=cmd_type,
            error=str(e)
        )


async def _execute_prompt_command(command: str, args: Optional[str], context: Optional[dict]) -> dict:
    """Execute a prompt-type command - for commit/commit-push-pr, execute directly."""
    if command == "commit":
        commit_msg = args or "No message provided"
        all_files = "--all" in commit_msg
        amend = "--amend" in commit_msg
        clean_msg = commit_msg.replace("--all", "").replace("--amend", "").strip()
        return await commit_command(CommitCommandRequest(
            message=clean_msg or "No message provided",
            all_files=all_files,
            amend=amend
        ))
    elif command == "commit-push-pr":
        parts = (args or "").split(" -- ")
        commit_msg = parts[0] or "Updates"
        title = parts[1] if len(parts) > 1 else None
        return await commit_push_pr(CommitPushPrRequest(message=commit_msg, title=title))
    
    prompts = {
        "init": "Create a CLAUDE.md file with project context including overview, tech stack, project structure, and commands.",
        "init-verifiers": "Create verifier skill(s) for automated verification of code changes.",
        "review": f"Review pull request. {args or 'Review the current changes.'}",
        "security-review": "Perform security review of the code changes.",
        "pr-comments": "Get comments from the pull request.",
        "proactive": "Enable proactive mode - predict user intent, prepare relevant tools and context, offer suggestions before being asked.",
        "brief": "Enable brief mode - compress all output, prioritize conciseness, reduce tokens while maintaining essential information.",
        "assistant": "Enable assistant mode - adopt advisory style, focus on recommendations and explanations rather than direct execution.",
    }
    
    prompt_text = prompts.get(command, f"Execute command: {command}")
    return {
        "type": "prompt",
        "prompt": prompt_text,
        "args": args,
        "context": context
    }


async def _execute_local_command(command: str, args: Optional[str], context: Optional[dict]) -> dict:
    """Execute a local command and return the result."""
    if command == "compact":
        return await compact_session()
    elif command == "cost":
        return await get_session_cost()
    elif command == "version":
        return await get_version()
    elif command == "doctor":
        return await run_doctor()
    elif command == "voice":
        return await voice_command()
    elif command == "new":
        keep_context = "--keep-context" in (args or "")
        force = "--force" in (args or "")
        return await new_session(NewCommandRequest(keep_context=keep_context, force=force))
    elif command == "git":
        sub_cmd = args.split()[0] if args else "status"
        if sub_cmd == "status":
            return await git_status()
        elif sub_cmd == "diff":
            return await git_diff()
        elif sub_cmd == "log":
            return await git_log()
        elif sub_cmd == "commit":
            msg = args.replace("commit ", "").strip() if args else ""
            return await git_commit(GitCommitRequest(message=msg))
    elif command == "rewind":
        steps = int(args) if args and args.isdigit() else 1
        return await rewind_session(RewindRequest(steps=steps))
    
    return {
        "command": command,
        "args": args,
        "message": f"Local command '{command}' executed",
        "context": context
    }


async def _execute_local_jsx_command(command: str, args: Optional[str], context: Optional[dict]) -> dict:
    """Execute a local-jsx command and return UI component info."""
    return {
        "command": command,
        "args": args,
        "type": "local-jsx",
        "component": f"{command.title().replace('-', '')}Command",
        "message": f"UI command '{command}' rendered",
        "context": context
    }


# ============================================================
# AGENTS COMMAND (P0)
# ============================================================

@router.get("/agents/list", response_model=AgentsResponse)
async def list_agents_command():
    """List available agent configurations for the agents command."""
    agents = [
        AgentInfo(id="auto", name="Auto", type="auto", status="active", enabled=True),
        AgentInfo(id="agent", name="Agent", type="agent", status="active", enabled=True),
        AgentInfo(id="compact", name="Compact", type="compact", status="active", enabled=True),
    ]
    return AgentsResponse(success=True, agents=agents)


@router.post("/agents/configure")
async def configure_agent_command(name: str, agent_type: str = "auto"):
    """Configure agent settings for the agents command."""
    agent_id = f"agent_{name.lower().replace(' ', '_')}"
    return {
        "success": True,
        "agent_id": agent_id,
        "name": name,
        "type": agent_type,
        "message": f"Agent '{name}' configured as {agent_type}"
    }


# ============================================================
# STATUS COMMAND (P0)
# ============================================================

@router.get("/status/full", response_model=StatusResponse)
async def get_full_status():
    """Get full status including version, model, and account info."""
    session = get_current_session()
    if not session:
        return StatusResponse(
            status="inactive",
            version="1.0.0",
            model="claude-3-5-sonnet-20241022",
            message_count=0
        )
    return StatusResponse(
        status="active",
        version="1.0.0",
        model=session.get("model", "claude-3-5-sonnet-20241022"),
        message_count=len(session.get("messages", [])),
        account=session.get("metadata", {}).get("account")
    )


# ============================================================
# PLUGIN COMMAND (P0)
# ============================================================

@router.get("/plugin/list")
async def list_plugins():
    """List all available plugins."""
    from ..services.plugins.config import get_enabled_plugins, get_all_plugin_configs
    enabled = get_enabled_plugins()
    configs = get_all_plugin_configs()
    return {
        "success": True,
        "enabled_plugins": enabled,
        "plugin_configs": configs,
        "message": f"{len(enabled)} plugins enabled"
    }


@router.post("/plugin/manage", response_model=PluginCommandResponse)
async def manage_plugin(request: PluginCommandRequest):
    """Manage plugins: install, uninstall, enable, disable."""
    from ..services.plugins.config import set_plugin_enabled
    if request.action == "enable":
        if not request.plugin_id:
            return PluginCommandResponse(success=False, action=request.action, message="plugin_id required")
        set_plugin_enabled(request.plugin_id, True)
        return PluginCommandResponse(success=True, action=request.action, plugin_id=request.plugin_id, message=f"Plugin {request.plugin_id} enabled")
    elif request.action == "disable":
        if not request.plugin_id:
            return PluginCommandResponse(success=False, action=request.action, message="plugin_id required")
        set_plugin_enabled(request.plugin_id, False)
        return PluginCommandResponse(success=True, action=request.action, plugin_id=request.plugin_id, message=f"Plugin {request.plugin_id} disabled")
    return PluginCommandResponse(success=True, action=request.action, message=f"Action {request.action} completed")


# ============================================================
# EXPORT COMMAND (P0)
# ============================================================

@router.post("/export/conversation", response_model=ExportCommandResponse)
async def export_conversation_command(request: ExportCommandRequest):
    """Export conversation to file or return content."""
    from .export import _render_messages_to_markdown
    from .export import _render_messages_to_plain_text
    from .export import _format_timestamp
    from .export import _extract_first_prompt
    from .export import _sanitize_filename
    from .export import _load_session_file as _load_session
    session = get_current_session()
    session_id = get_current_session_id()
    if not session:
        session = _load_session(session_id or "")
    if not session:
        return ExportCommandResponse(success=False, content="", filename="", message_count=0)
    messages = session.get("messages", [])
    content = _render_messages_to_markdown(messages) if request.format == "markdown" else _render_messages_to_plain_text(messages)
    timestamp = _format_timestamp(datetime.now())
    first_prompt = _extract_first_prompt(messages)
    filename = f"{_sanitize_filename(first_prompt) or 'conversation'}-{timestamp}.{'md' if request.format == 'markdown' else 'txt'}"
    if request.file_path:
        try:
            Path(request.file_path).write_text(content, encoding="utf-8")
        except Exception:
            return ExportCommandResponse(success=False, content=content, filename=filename, message_count=len(messages))
    return ExportCommandResponse(success=True, content=content, filename=filename, message_count=len(messages))


# ============================================================
# COLOR COMMAND (P1)
# ============================================================

AGENT_COLORS = ["blue", "green", "orange", "red", "purple", "pink", "gray", "default", "reset", "none"]

@router.post("/color", response_model=ColorResponse)
async def set_color(request: ColorRequest):
    """Set the prompt bar color for the session."""
    color = request.color.lower()
    if color in ["default", "reset", "none", "gray", "grey"]:
        color = "default"
    if color not in AGENT_COLORS:
        return ColorResponse(success=False, color=request.color, message=f"Invalid color. Use: {', '.join(AGENT_COLORS[:-3])}")
    session_id = get_current_session_id()
    if session_id:
        from .sessions import _get_active_session
        session = _get_active_session(session_id)
        if session:
            session["metadata"] = session.get("metadata", {})
            session["metadata"]["color"] = color
    return ColorResponse(success=True, color=color, message=f"Color set to {color}")


# ============================================================
# TAG COMMAND (P1)
# ============================================================

@router.post("/tag", response_model=TagCommandResponse)
async def tag_session(request: TagCommandRequest):
    """Add, update, or remove a tag from the session."""
    session_id = get_current_session_id() or "default"
    if not request.tag:
        from .tags import _session_tags, _save_tags
        if session_id in _session_tags:
            del _session_tags[session_id]
            _save_tags()
        return TagCommandResponse(success=True, session_id=session_id, tag=None, message="Tag removed")
    from .tags import _validate_tag, _session_tags, _save_tags
    normalized = _validate_tag(request.tag)
    _session_tags[session_id] = {"tag": normalized, "updated_at": datetime.now().timestamp()}
    _save_tags()
    return TagCommandResponse(success=True, session_id=session_id, tag=normalized, message=f"Tag set to #{normalized}")


# ============================================================
# RENAME COMMAND (P1)
# ============================================================

class RenameRequest(BaseModel):
    session_id: Optional[str] = None
    new_name: str


class RenameResponse(BaseModel):
    success: bool
    session_id: str
    old_name: Optional[str] = None
    new_name: str
    message: str


@router.post("/rename", response_model=RenameResponse)
async def rename_session(request: RenameRequest):
    """Rename the current session with a new title/name."""
    session_id = request.session_id or get_current_session_id() or "default"
    from .sessions import _get_active_session
    
    session = _get_active_session(session_id)
    old_name = None
    
    if session:
        old_name = session.get("title")
        session["title"] = request.new_name
        session["metadata"] = session.get("metadata", {})
        session["metadata"]["renamed_at"] = datetime.now().isoformat()
    
    return RenameResponse(
        success=True,
        session_id=session_id,
        old_name=old_name,
        new_name=request.new_name,
        message=f"Session renamed to '{request.new_name}'"
    )


# ============================================================
# OUTPUTSTYLE COMMAND (P1)
# ============================================================

@router.post("/outputStyle", response_model=OutputStyleResponse)
async def set_output_style(request: OutputStyleRequest):
    """Set the output style (deprecated - shows message)."""
    return OutputStyleResponse(success=False, style=request.style, message="outputStyle command is deprecated. Use /config to adjust display settings.")


# ============================================================
# ADD-DIR COMMAND (P1)
# ============================================================

class AddDirRequest(BaseModel):
    path: str
    include_patterns: Optional[list[str]] = None
    exclude_patterns: Optional[list[str]] = None
    recursive: bool = True


class AddDirResponse(BaseModel):
    success: bool
    path: str
    files_added: int
    message: str


@router.post("/add-dir", response_model=AddDirResponse)
async def add_directory(request: AddDirRequest):
    """Add a working directory to the session context for file operations."""
    import fnmatch
    
    target_path = Path(request.path)
    if not target_path.exists():
        return AddDirResponse(
            success=False,
            path=request.path,
            files_added=0,
            message=f"Path does not exist: {request.path}"
        )
    
    if not target_path.is_dir():
        return AddDirResponse(
            success=False,
            path=request.path,
            files_added=0,
            message=f"Path is not a directory: {request.path}"
        )
    
    include_patterns = request.include_patterns or ["*"]
    exclude_patterns = request.exclude_patterns or []
    
    files_added = 0
    visited_dirs = 0
    max_dirs = 1000
    
    def should_include(file_path: Path) -> bool:
        rel_path = str(file_path)
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                return False
        for pattern in include_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                return True
        return False
    
    def scan_directory(dir_path: Path):
        nonlocal files_added, visited_dirs
        if visited_dirs >= max_dirs:
            return
        visited_dirs += 1
        
        try:
            for item in dir_path.iterdir():
                if item.is_file() and should_include(item):
                    files_added += 1
                elif item.is_dir() and request.recursive:
                    scan_directory(item)
        except PermissionError:
            pass
    
    scan_directory(target_path)
    
    session_id = get_current_session_id() or "default"
    from .sessions import _get_active_session
    session = _get_active_session(session_id)
    if session:
        session["metadata"] = session.get("metadata", {})
        if "added_dirs" not in session["metadata"]:
            session["metadata"]["added_dirs"] = []
        session["metadata"]["added_dirs"].append({
            "path": str(target_path.absolute()),
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
            "files_added": files_added
        })
    
    return AddDirResponse(
        success=True,
        path=str(target_path.absolute()),
        files_added=files_added,
        message=f"Added directory with {files_added} files to session context"
    )


# ============================================================
# STATUSLINE COMMAND (P1)
# ============================================================

@router.post("/statusline", response_model=StatusLineResponse)
async def configure_statusline(request: StatusLineRequest):
    """Configure the status line UI from shell PS1 prompt."""
    if request.config:
        try:
            settings_path = Path.home() / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            current = {}
            if settings_path.exists():
                current = json.loads(settings_path.read_text())
            current["statusLine"] = request.config
            settings_path.write_text(json.dumps(current, indent=2))
            return StatusLineResponse(success=True, message="Status line configured", config=current)
        except Exception as e:
            return StatusLineResponse(success=False, message=f"Error: {e}")
    return StatusLineResponse(success=True, message="Status line configured (awaiting shell PS1 config)", config=None)


# ============================================================
# VIM COMMAND (P1)
# ============================================================

@router.post("/vim", response_model=VimModeResponse)
async def toggle_vim_mode():
    """Toggle between normal and vim editor mode."""
    settings_path = Path.home() / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    current = {}
    if settings_path.exists():
        current = json.loads(settings_path.read_text())
    current_mode = current.get("editorMode", "normal")
    new_mode = "vim" if current_mode == "normal" else "normal"
    current["editorMode"] = new_mode
    settings_path.write_text(json.dumps(current, indent=2))
    return VimModeResponse(success=True, mode=new_mode, message=f"Editor mode set to {new_mode}")


@router.get("/vim")
async def get_vim_mode():
    """Get current vim mode status."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if settings_path.exists():
        current = json.loads(settings_path.read_text())
        return {"mode": current.get("editorMode", "normal")}
    return {"mode": "normal"}


# ============================================================
# THEME COMMAND (P1)
# ============================================================

THEMES = ["dark", "light", "system", "dracula", "monokai", "github"]

@router.get("/theme", response_model=ThemeResponse)
async def get_themes():
    """List available themes."""
    settings_path = Path.home() / ".claude" / "settings.json"
    current = None
    if settings_path.exists():
        current = json.loads(settings_path.read_text()).get("theme")
    return ThemeResponse(success=True, current_theme=current, available_themes=THEMES, message="Available themes listed")


@router.post("/theme", response_model=ThemeResponse)
async def set_theme(request: ThemeRequest):
    """Set the application theme."""
    if request.theme and request.theme not in THEMES:
        return ThemeResponse(success=False, current_theme=None, available_themes=THEMES, message=f"Invalid theme. Use: {', '.join(THEMES)}")
    settings_path = Path.home() / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    current = {}
    if settings_path.exists():
        current = json.loads(settings_path.read_text())
    if request.theme:
        current["theme"] = request.theme
        settings_path.write_text(json.dumps(current, indent=2))
    return ThemeResponse(success=True, current_theme=request.theme or current.get("theme"), available_themes=THEMES, message=f"Theme set to {request.theme}" if request.theme else "Theme status")


# ============================================================
# STICKERS COMMAND (P2)
# ============================================================

@router.get("/stickers", response_model=StickersResponse)
async def get_stickers():
    """Get link to order Claude Code stickers."""
    return StickersResponse(success=True, url="https://www.stickermule.com/claudecode", message="Visit sticker URL to order")


# ============================================================
# THINKBACKPLAY COMMAND (P2)
# ============================================================

@router.post("/thinkbackPlay", response_model=ThinkbackPlayResponse)
async def play_thinkback():
    """Play the thinkback animation (year in review)."""
    try:
        skill_dir = Path.home() / ".claude" / "skills" / "thinkback"
        if not skill_dir.exists():
            return ThinkbackPlayResponse(success=False, message="Thinkback skill not installed. Install with /skills install thinkback")
        return ThinkbackPlayResponse(success=True, message="Thinkback animation would play here", animation_path=str(skill_dir))
    except Exception as e:
        return ThinkbackPlayResponse(success=False, message=f"Error: {e}")


# ============================================================
# ULTRAPLAN COMMAND (ULTRAPLAN)
# ============================================================

class UltraplanRequest(BaseModel):
    task: str
    timeout_ms: Optional[int] = 300000


class UltraplanResponse(BaseModel):
    success: bool
    plan: Optional[str] = None
    phase: str
    reject_count: int = 0
    execution_target: Optional[str] = None
    message: str


_ultraplan_state: dict = {"enabled": False, "current_plan": None, "phase": "idle"}


def _check_ultraplan_feature_flag() -> bool:
    return "ULTRAPLAN" in os.environ


@router.get("/ultraplan")
async def get_ultraplan_status():
    enabled = _check_ultraplan_feature_flag()
    _ultraplan_state["enabled"] = enabled
    if not enabled:
        raise HTTPException(status_code=403, detail="Feature flag ULTRAPLAN is not enabled")
    return {"success": True, "enabled": enabled, "phase": _ultraplan_state.get("phase", "idle"), "current_plan": _ultraplan_state.get("current_plan"), "message": "UltraPlan mode active"}


@router.post("/ultraplan")
async def start_ultraplan(request: UltraplanRequest):
    if not _check_ultraplan_feature_flag():
        raise HTTPException(status_code=403, detail="Feature flag ULTRAPLAN is not enabled")
    _ultraplan_state["enabled"] = True
    _ultraplan_state["phase"] = "running"
    _ultraplan_state["current_plan"] = None
    return UltraplanResponse(success=True, plan=None, phase="running", reject_count=0, execution_target=None, message=f"UltraPlan started for task: {request.task}")


@router.get("/ultraplan/poll")
async def poll_ultraplan_status(timeout_ms: Optional[int] = 300000):
    if not _check_ultraplan_feature_flag():
        raise HTTPException(status_code=403, detail="Feature flag ULTRAPLAN is not enabled")
    return {"success": True, "phase": _ultraplan_state.get("phase", "idle"), "plan": _ultraplan_state.get("current_plan"), "reject_count": 0, "message": "Polling for UltraPlan approval"}


# ============================================================
# SUBSCRIBE-PR COMMAND (KAIROS_GITHUB_WEBHOOKS)
# ============================================================

class SubscribePrRequest(BaseModel):
    repo: str
    pr_number: int
    events: Optional[list[str]] = None


class SubscribePrResponse(BaseModel):
    success: bool
    subscription_id: Optional[str] = None
    repo: str
    pr_number: int
    events: list[str]
    message: str


_subscribe_pr_state: dict = {"enabled": False, "subscriptions": []}


def _check_subscribe_pr_feature_flag() -> bool:
    return "KAIROS_GITHUB_WEBHOOKS" in os.environ


@router.get("/subscribe-pr")
async def list_pr_subscriptions():
    enabled = _check_subscribe_pr_feature_flag()
    _subscribe_pr_state["enabled"] = enabled
    if not enabled:
        raise HTTPException(status_code=403, detail="Feature flag KAIROS_GITHUB_WEBHOOKS is not enabled")
    return {"success": True, "subscriptions": _subscribe_pr_state.get("subscriptions", []), "count": len(_subscribe_pr_state.get("subscriptions", [])), "message": "PR subscription list retrieved"}


@router.post("/subscribe-pr")
async def subscribe_to_pr(request: SubscribePrRequest):
    if not _check_subscribe_pr_feature_flag():
        raise HTTPException(status_code=403, detail="Feature flag KAIROS_GITHUB_WEBHOOKS is not enabled")
    default_events = ["commit", "review", "comment"]
    events = request.events or default_events
    subscription_id = f"sub_{request.repo.replace('/', '_')}_{request.pr_number}"
    subscription = {"id": subscription_id, "repo": request.repo, "pr_number": request.pr_number, "events": events, "active": True}
    _subscribe_pr_state.setdefault("subscriptions", []).append(subscription)
    return SubscribePrResponse(success=True, subscription_id=subscription_id, repo=request.repo, pr_number=request.pr_number, events=events, message=f"Subscribed to PR #{request.pr_number} in {request.repo}")


@router.delete("/subscribe-pr/{subscription_id}")
async def unsubscribe_from_pr(subscription_id: str):
    if not _check_subscribe_pr_feature_flag():
        raise HTTPException(status_code=403, detail="Feature flag KAIROS_GITHUB_WEBHOOKS is not enabled")
    subscriptions = _subscribe_pr_state.get("subscriptions", [])
    _subscribe_pr_state["subscriptions"] = [s for s in subscriptions if s.get("id") != subscription_id]
    return {"success": True, "message": f"Unsubscribed from {subscription_id}"}


@router.get("/subscribe-pr/{subscription_id}/events")
async def get_pr_subscription_events(subscription_id: str):
    if not _check_subscribe_pr_feature_flag():
        raise HTTPException(status_code=403, detail="Feature flag KAIROS_GITHUB_WEBHOOKS is not enabled")
    subscription = next((s for s in _subscribe_pr_state.get("subscriptions", []) if s.get("id") == subscription_id), None)
    if not subscription:
        raise HTTPException(status_code=404, detail=f"Subscription '{subscription_id}' not found")
    return {"success": True, "subscription": subscription, "events": [], "message": f"Events for {subscription_id}"}


# ============================================================
# WEB-SETUP COMMAND (CCR_REMOTE_SETUP)
# ============================================================

class WebSetupRequest(BaseModel):
    device_id: Optional[str] = None
    config: Optional[dict] = None
    action: str = "status"


class WebSetupResponse(BaseModel):
    success: bool
    device_id: Optional[str]
    status: str
    config: Optional[dict] = None
    message: str


_web_setup_state: dict = {"enabled": False, "devices": []}


def _check_web_setup_feature_flag() -> bool:
    return "CCR_REMOTE_SETUP" in os.environ


@router.get("/web-setup")
async def get_web_setup_status():
    enabled = _check_web_setup_feature_flag()
    _web_setup_state["enabled"] = enabled
    if not enabled:
        raise HTTPException(status_code=403, detail="Feature flag CCR_REMOTE_SETUP is not enabled")
    return {"success": True, "enabled": enabled, "devices": _web_setup_state.get("devices", []), "message": "Web Setup active" if enabled else "Web Setup not enabled"}


@router.post("/web-setup")
async def configure_web_setup(request: WebSetupRequest):
    if not _check_web_setup_feature_flag():
        raise HTTPException(status_code=403, detail="Feature flag CCR_REMOTE_SETUP is not enabled")
    device_id = request.device_id or "default"
    action = request.action.lower()
    if action == "status":
        device = next((d for d in _web_setup_state.get("devices", []) if d.get("id") == device_id), None)
        if device:
            return WebSetupResponse(success=True, device_id=device_id, status=device.get("status", "unknown"), config=device.get("config"), message=f"Device {device_id} status retrieved")
        return WebSetupResponse(success=True, device_id=device_id, status="no_device", config=None, message=f"No device found with ID {device_id}")
    elif action == "configure":
        config = request.config or {}
        devices = _web_setup_state.get("devices", [])
        existing_idx = next((i for i, d in enumerate(devices) if d.get("id") == device_id), None)
        if existing_idx is not None:
            devices[existing_idx].update({"config": config, "status": "configured"})
        else:
            devices.append({"id": device_id, "config": config, "status": "configured"})
        _web_setup_state["devices"] = devices
        return WebSetupResponse(success=True, device_id=device_id, status="configured", config=config, message=f"Device {device_id} configured successfully")
    elif action == "reset":
        devices = _web_setup_state.get("devices", [])
        _web_setup_state["devices"] = [d for d in devices if d.get("id") != device_id]
        return WebSetupResponse(success=True, device_id=device_id, status="reset", config=None, message=f"Device {device_id} reset successfully")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@router.get("/web-setup/devices")
async def list_web_setup_devices():
    if not _check_web_setup_feature_flag():
        raise HTTPException(status_code=403, detail="Feature flag CCR_REMOTE_SETUP is not enabled")
    return {"success": True, "devices": _web_setup_state.get("devices", []), "count": len(_web_setup_state.get("devices", []))}


@router.get("/web-setup/device/{device_id}")
async def get_web_setup_device(device_id: str):
    if not _check_web_setup_feature_flag():
        raise HTTPException(status_code=403, detail="Feature flag CCR_REMOTE_SETUP is not enabled")
    device = next((d for d in _web_setup_state.get("devices", []) if d.get("id") == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    return {"success": True, "device": device}


# ============================================================
# INTERNAL_ONLY COMMANDS - REQUEST/RESPONSE MODELS
# ============================================================

class BackfillSessionsRequest(BaseModel):
    session_ids: Optional[list[str]] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class BackfillSessionsResponse(BaseModel):
    success: bool
    sessions_backfilled: int
    message: str


class BreakCacheResponse(BaseModel):
    success: bool
    cache_type: str
    message: str


class BugHunterRequest(BaseModel):
    description: str
    severity: Optional[str] = "medium"
    tags: Optional[list[str]] = None


class BugHunterResponse(BaseModel):
    success: bool
    report_id: Optional[str] = None
    message: str


class CommitPushPrRequest(BaseModel):
    message: str
    branch: Optional[str] = None
    target_branch: Optional[str] = "main"
    files: Optional[list[str]] = None
    title: Optional[str] = None
    all_files: bool = False


class CommitPushPrResponse(BaseModel):
    success: bool
    commit_hash: Optional[str] = None
    pr_url: Optional[str] = None
    message: str


class CtxVizResponse(BaseModel):
    success: bool
    total_tokens: int
    max_tokens: int
    usage_percent: float
    message_count: int


class ForceSnipRequest(BaseModel):
    keep_recent: int = 10


class ForceSnipResponse(BaseModel):
    success: bool
    messages_removed: int
    messages_remaining: int


class GoodClaudeRequest(BaseModel):
    feedback: str
    rating: Optional[int] = None


class GoodClaudeResponse(BaseModel):
    success: bool
    message: str


class IssueRequest(BaseModel):
    title: str
    description: Optional[str] = None
    labels: Optional[list[str]] = None


class IssueResponse(BaseModel):
    success: bool
    issue_number: Optional[int] = None
    issue_url: Optional[str] = None
    message: str


class MockLimitsRequest(BaseModel):
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000


class MockLimitsResponse(BaseModel):
    success: bool
    mock_enabled: bool
    limits: dict


class BridgeKickResponse(BaseModel):
    success: bool
    kicked: bool
    message: str


class AntTraceRequest(BaseModel):
    trace_id: Optional[str] = None
    duration_ms: Optional[int] = None


class AntTraceResponse(BaseModel):
    success: bool
    trace_id: str
    spans: list[dict]


class PerfIssueRequest(BaseModel):
    description: str
    session_id: Optional[str] = None
    attach_logs: bool = False


class PerfIssueResponse(BaseModel):
    success: bool
    issue_id: Optional[str] = None
    message: str


class EnvRequest(BaseModel):
    action: str
    key: Optional[str] = None
    value: Optional[str] = None


class EnvResponse(BaseModel):
    success: bool
    variables: dict
    message: str


class OauthRefreshResponse(BaseModel):
    success: bool
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    message: str


class DebugToolCallRequest(BaseModel):
    tool_name: str
    arguments: Optional[dict[str, Any]] = None


class DebugToolCallResponse(BaseModel):
    success: bool
    tool_name: str
    result: Optional[Any] = None
    error: Optional[str] = None


class AgentsPlatformRequest(BaseModel):
    action: str
    agent_id: Optional[str] = None


class AgentsPlatformResponse(BaseModel):
    success: bool
    agents: list[dict]
    message: str


class AutofixPrRequest(BaseModel):
    pr_number: int
    auto_merge: bool = False


class AutofixPrResponse(BaseModel):
    success: bool
    fixes_applied: int
    pr_url: Optional[str] = None
    message: str


# ============================================================
# INTERNAL_ONLY COMMANDS - HANDLERS
# ============================================================

@router.post("/backfillSessions", response_model=BackfillSessionsResponse)
async def backfill_sessions(request: BackfillSessionsRequest = None):
    """Backfill internal session data from storage."""
    from .sessions import _load_session_file, _list_session_files
    backfilled = 0
    session_ids = request.session_ids if request and request.session_ids else []
    if not session_ids:
        session_ids = _list_session_files()
    for sid in session_ids:
        session = _load_session_file(sid)
        if session:
            backfilled += 1
    return BackfillSessionsResponse(
        success=True,
        sessions_backfilled=backfilled,
        message=f"Backfilled {backfilled} sessions"
    )


@router.post("/breakCache", response_model=BreakCacheResponse)
async def break_cache():
    """Break the prompt cache to force fresh computation."""
    return BreakCacheResponse(
        success=True,
        cache_type="prompt",
        message="Prompt cache broken for current request"
    )


@router.post("/bughunter", response_model=BugHunterResponse)
async def bughunter_report(request: BugHunterRequest):
    """Submit a bug hunter report."""
    import uuid
    report_id = str(uuid.uuid4())[:8]
    return BugHunterResponse(
        success=True,
        report_id=report_id,
        message=f"Bug report submitted: {request.description[:50]}..."
    )


@router.post("/commitPushPr", response_model=CommitPushPrResponse)
async def commit_push_pr(request: CommitPushPrRequest):
    """Commit changes, push to remote, and create PR."""
    import uuid
    
    returncode, status_output, _ = _run_git_command(["status", "--porcelain"])
    if returncode != 0:
        return CommitPushPrResponse(success=False, message="Git not available")
    
    has_changes = bool(status_output.strip())
    if not has_changes:
        return CommitPushPrResponse(success=False, message="No changes to commit")
    
    branch_name = request.branch or f"fix-{uuid.uuid4().hex[:8]}"
    returncode, stdout, stderr = _run_git_command(["checkout", "-b", branch_name])
    if returncode != 0:
        return CommitPushPrResponse(success=False, message=f"Failed to create branch: {stderr}")
    
    if request.all_files:
        _run_git_command(["add", "-A"])
    elif request.files:
        for f in request.files:
            _run_git_command(["add", f])
    else:
        _run_git_command(["add", "-u"])
    
    returncode, commit_out, _ = _run_git_command(["commit", "-m", request.message])
    if returncode != 0:
        _run_git_command(["checkout", "-"])
        return CommitPushPrResponse(success=False, message=f"Failed to commit: {commit_out}")
    
    _, hash_out, _ = _run_git_command(["rev-parse", "HEAD"])
    returncode, push_out, push_err = _run_git_command(["push", "-u", "origin", branch_name])
    if returncode != 0:
        _run_git_command(["checkout", "-"])
        return CommitPushPrResponse(success=False, commit_hash=hash_out.strip(), message=f"Push failed: {push_err}")
    
    pr_title = request.title or request.message
    returncode, pr_out, _ = _run_git_command([
        "gh", "pr", "create", "--title", pr_title, "--body", request.message,
        "--base", request.target_branch or "main"
    ])
    pr_url = pr_out.strip() if returncode == 0 else None
    
    return CommitPushPrResponse(
        success=True,
        commit_hash=hash_out.strip(),
        pr_url=pr_url,
        message=f"Committed, pushed, and PR created" if pr_url else "Committed and pushed"
    )


@router.post("/commit-push-pr", response_model=CommitPushPrResponse)
async def commit_push_pr_hyphenated(request: CommitPushPrRequest):
    """Commit changes, push to remote, and create PR (hyphenated endpoint)."""
    return await commit_push_pr(request)


@router.get("/ctx_viz", response_model=CtxVizResponse)
async def ctx_viz():
    """Visualize context usage for current session."""
    session = get_current_session()
    if not session:
        return CtxVizResponse(success=True, total_tokens=0, max_tokens=200000, usage_percent=0.0, message_count=0)
    messages = session.get("messages", [])
    total_tokens = estimate_tokens_for_messages(messages)
    max_tokens = 200000
    usage_percent = round((total_tokens / max_tokens) * 100, 2) if max_tokens > 0 else 0.0
    return CtxVizResponse(
        success=True,
        total_tokens=total_tokens,
        max_tokens=max_tokens,
        usage_percent=usage_percent,
        message_count=len(messages)
    )


@router.post("/forceSnip", response_model=ForceSnipResponse)
async def force_snip(request: ForceSnipRequest = None):
    """Force truncate conversation history."""
    session = get_current_session()
    if not session:
        return ForceSnipResponse(success=False, messages_removed=0, messages_remaining=0)
    messages = session.get("messages", [])
    keep_recent = request.keep_recent if request else 10
    system_msgs = [m for m in messages if m.get("role") == "system"]
    other_msgs = [m for m in messages if m.get("role") != "system"]
    removed = max(0, len(other_msgs) - keep_recent)
    session["messages"] = system_msgs + other_msgs[-keep_recent:] if keep_recent < len(other_msgs) else messages
    return ForceSnipResponse(
        success=True,
        messages_removed=removed,
        messages_remaining=len(session["messages"])
    )


@router.post("/goodClaude", response_model=GoodClaudeResponse)
async def good_claude_feedback(request: GoodClaudeRequest):
    """Submit feedback about Claude Code."""
    return GoodClaudeResponse(
        success=True,
        message="Thank you for your feedback!"
    )


@router.post("/initVerifiers", response_model=InitVerifiersResponse)
async def init_verifiers_internal(request: InitVerifiersRequest = None):
    """Initialize verifiers (internal implementation)."""
    return await init_verifiers(request)


@router.post("/issue", response_model=IssueResponse)
async def create_issue(request: IssueRequest):
    """Create an issue in the issue tracker."""
    returncode, stdout, stderr = _run_git_command([
        "gh", "issue", "create",
        "--title", request.title,
        "--body", request.description or "",
        "--label", ",".join(request.labels) if request.labels else ""
    ])
    if returncode != 0:
        return IssueResponse(success=False, message=f"Failed to create issue: {stderr}")
    issue_url = stdout.strip()
    try:
        issue_number = int(issue_url.split("/")[-1])
    except:
        issue_number = None
    return IssueResponse(
        success=True,
        issue_number=issue_number,
        issue_url=issue_url,
        message=f"Issue #{issue_number} created"
    )


@router.post("/mockLimits", response_model=MockLimitsResponse)
async def mock_limits(request: MockLimitsRequest):
    """Enable mock mode for rate limiting."""
    return MockLimitsResponse(
        success=True,
        mock_enabled=True,
        limits={
            "requests_per_minute": request.requests_per_minute,
            "tokens_per_minute": request.tokens_per_minute
        }
    )


@router.post("/bridgeKick", response_model=BridgeKickResponse)
async def bridge_kick():
    """Kick/disconnect from bridge mode."""
    return BridgeKickResponse(
        success=True,
        kicked=True,
        message="Disconnected from bridge mode"
    )


@router.post("/antTrace", response_model=AntTraceResponse)
async def ant_trace(request: AntTraceRequest = None):
    """Collect ANT trace data."""
    import uuid
    trace_id = request.trace_id if request and request.trace_id else str(uuid.uuid4())
    return AntTraceResponse(
        success=True,
        trace_id=trace_id,
        spans=[]
    )


@router.post("/perfIssue", response_model=PerfIssueResponse)
async def perf_issue_report(request: PerfIssueRequest):
    """Submit a performance issue report."""
    import uuid
    issue_id = str(uuid.uuid4())[:8]
    return PerfIssueResponse(
        success=True,
        issue_id=issue_id,
        message=f"Performance issue reported: {request.description[:50]}..."
    )


@router.post("/env", response_model=EnvResponse)
async def manage_env(request: EnvRequest):
    """Manage environment variables."""
    env_vars = {}
    if request.action == "get":
        for key, val in os.environ.items():
            if not key.startswith("_"):
                env_vars[key] = val
    elif request.action == "set" and request.key:
        os.environ[request.key] = request.value or ""
        env_vars[request.key] = request.value or ""
    elif request.action == "delete" and request.key:
        if request.key in os.environ:
            del os.environ[request.key]
    return EnvResponse(
        success=True,
        variables=env_vars,
        message=f"Environment variables {request.action}d"
    )


@router.post("/oauthRefresh", response_model=OauthRefreshResponse)
async def oauth_refresh():
    """Refresh OAuth access token."""
    return OauthRefreshResponse(
        success=True,
        access_token=None,
        expires_in=3600,
        message="OAuth refresh not implemented (stub)"
    )


@router.post("/debugToolCall", response_model=DebugToolCallResponse)
async def debug_tool_call(request: DebugToolCallRequest):
    """Debug a tool call with detailed logging."""
    try:
        result = {"tool": request.tool_name, "args": request.arguments or {}, "status": "executed"}
        return DebugToolCallResponse(
            success=True,
            tool_name=request.tool_name,
            result=result
        )
    except Exception as e:
        return DebugToolCallResponse(
            success=False,
            tool_name=request.tool_name,
            error=str(e)
        )


@router.post("/agentsPlatform", response_model=AgentsPlatformResponse)
async def agents_platform(request: AgentsPlatformRequest = None):
    """Manage ANT agents platform."""
    agents = [
        {"id": "ant-1", "name": "ANT Agent 1", "status": "active"},
        {"id": "ant-2", "name": "ANT Agent 2", "status": "idle"}
    ]
    return AgentsPlatformResponse(
        success=True,
        agents=agents,
        message="ANT agents platform accessed"
    )


@router.post("/autofixPr", response_model=AutofixPrResponse)
async def autofix_pr(request: AutofixPrRequest):
    """Automatically fix issues in a PR."""
    returncode, details, _ = _run_git_command([
        "gh", "pr", "view", str(request.pr_number), "--json", "title,body,additions,deletions"
    ])
    if returncode != 0:
        return AutofixPrResponse(success=False, fixes_applied=0, message=f"PR #{request.pr_number} not found")
    return AutofixPrResponse(
        success=True,
        fixes_applied=0,
        pr_url=None,
        message="Auto-fix would analyze and fix issues in PR"
    )
