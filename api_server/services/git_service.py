import asyncio
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Awaitable, Optional


@dataclass
class GitStatus:
    branch: str
    is_dirty: bool
    staged_files: list[str] = field(default_factory=list)
    unstaged_files: list[str] = field(default_factory=list)
    untracked_files: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0


@dataclass
class GitCommitResult:
    success: bool
    commit_hash: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


@dataclass
class GitBranch:
    name: str
    is_current: bool
    is_remote: bool = False


async def _run_git_command(args: list[str], cwd: Optional[str] = None) -> tuple[int, str, str]:
    loop = asyncio.get_event_loop()
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=cwd or Path.cwd(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
    except FileNotFoundError:
        return -1, "", "Git not found"
    except Exception as e:
        return -1, "", str(e)


async def get_git_status(cwd: str | None = None) -> GitStatus | None:
    returncode, stdout, stderr = await _run_git_command(["status", "--porcelain"], cwd)
    if returncode != 0:
        return None
    
    status = GitStatus(branch="", is_dirty=False)
    
    _, branch_stdout, _ = await _run_git_command(["branch", "--show-current"], cwd)
    status.branch = branch_stdout.strip() or "HEAD"
    
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        status.is_dirty = True
        status_code = line[:2]
        filepath = line[3:]
        
        if status_code == "??":
            status.untracked_files.append(filepath)
        elif status_code[0] in "MAD":
            status.staged_files.append(filepath)
        elif status_code[1] in "MAD":
            status.unstaged_files.append(filepath)
    
    return status


async def get_git_diff(cwd: str | None = None, file_path: str | None = None) -> str:
    args = ["diff"]
    if file_path:
        args.append(file_path)
    
    returncode, stdout, stderr = await _run_git_command(args, cwd)
    if returncode != 0:
        return f"Error: {stderr}"
    return stdout


async def get_git_log(limit: int = 50, cwd: str | None = None) -> list[dict]:
    returncode, stdout, stderr = await _run_git_command([
        "log", f"-{limit}",
        "--format=%H|%s|%an|%ae|%ad",
        "--date=iso"
    ], cwd)
    
    if returncode != 0:
        return []
    
    commits = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|")
        if len(parts) >= 5:
            commits.append({
                "hash": parts[0],
                "message": parts[1],
                "author": parts[2],
                "email": parts[3],
                "date": parts[4],
            })
    return commits


async def git_add(files: list[str], cwd: str | None = None) -> str:
    if not files:
        returncode, _, stderr = await _run_git_command(["add", "."], cwd)
        if returncode != 0:
            return f"Error: {stderr}"
        return "Added all changes"
    
    returncode, stdout, stderr = await _run_git_command(["add"] + files, cwd)
    if returncode != 0:
        return f"Error: {stderr}"
    return stdout or f"Added {len(files)} file(s)"


async def git_commit(message: str, cwd: str | None = None) -> GitCommitResult:
    if not message or not message.strip():
        return GitCommitResult(success=False, error="Commit message is required")
    
    returncode, stdout, stderr = await _run_git_command(["commit", "-m", message], cwd)
    
    if returncode != 0:
        if "nothing to commit" in stderr.lower():
            return GitCommitResult(success=False, error="Nothing to commit")
        if "no changes added" in stderr.lower():
            return GitCommitResult(success=False, error="No changes to commit")
        return GitCommitResult(success=False, error=stderr)
    
    _, hash_stdout, _ = await _run_git_command(["rev-parse", "HEAD"], cwd)
    commit_hash = hash_stdout.strip()[:8]
    
    return GitCommitResult(success=True, commit_hash=commit_hash, message=message)


async def git_branch(cwd: str | None = None) -> list[GitBranch]:
    returncode, stdout, stderr = await _run_git_command(["branch", "-a"], cwd)
    
    if returncode != 0:
        return []
    
    branches = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        name = line[2:] if line.startswith("* ") else line
        is_current = line.startswith("* ")
        is_remote = line.startswith("remotes/") or "/" in name
        branches.append(GitBranch(
            name=name.strip(),
            is_current=is_current,
            is_remote=is_remote,
        ))
    return branches


async def git_checkout(branch: str, cwd: str | None = None, create: bool = False) -> str:
    args = ["checkout"]
    if create:
        args.append("-b")
    args.append(branch)
    
    returncode, stdout, stderr = await _run_git_command(args, cwd)
    
    if returncode != 0:
        return f"Error: {stderr}"
    return stdout or f"Switched to branch: {branch}"


async def git_push(remote: str = "origin", branch: str | None = None, cwd: str | None = None) -> str:
    args = ["push", remote]
    if branch:
        args.append(branch)
    
    returncode, stdout, stderr = await _run_git_command(args, cwd)
    
    if returncode != 0:
        return f"Error: {stderr}"
    return stdout or f"Pushed to {remote}"


async def git_pull(remote: str = "origin", branch: str | None = None, cwd: str | None = None) -> str:
    args = ["pull", remote]
    if branch:
        args.append(branch)
    
    returncode, stdout, stderr = await _run_git_command(args, cwd)
    
    if returncode != 0:
        return f"Error: {stderr}"
    return stdout or f"Pulled from {remote}"


async def git_stash(cwd: str | None = None) -> str:
    returncode, stdout, stderr = await _run_git_command(["stash"], cwd)
    
    if returncode != 0:
        return f"Error: {stderr}"
    return stdout or "Changes stashed"


async def git_stash_pop(cwd: str | None = None) -> str:
    returncode, stdout, stderr = await _run_git_command(["stash", "pop"], cwd)
    
    if returncode != 0:
        return f"Error: {stderr}"
    return stdout or "Changes restored from stash"


async def git_merge(branch: str, cwd: str | None = None) -> str:
    returncode, stdout, stderr = await _run_git_command(["merge", branch], cwd)
    
    if returncode != 0:
        if "already up to date" in stderr.lower():
            return "Already up to date"
        if "conflict" in stderr.lower():
            return f"Merge conflict with {branch}"
        return f"Error: {stderr}"
    return stdout or f"Merged {branch}"


async def git_rebase(branch: str, cwd: str | None = None) -> str:
    returncode, stdout, stderr = await _run_git_command(["rebase", branch], cwd)
    
    if returncode != 0:
        if "already up to date" in stderr.lower():
            return "Already up to date"
        return f"Error: {stderr}"
    return stdout or f"Rebased onto {branch}"


async def git_fetch(remote: str = "origin", cwd: str | None = None) -> str:
    returncode, stdout, stderr = await _run_git_command(["fetch", remote], cwd)
    
    if returncode != 0:
        return f"Error: {stderr}"
    return stdout or f"Fetched from {remote}"


async def git_remote_list(cwd: str | None = None) -> list[dict]:
    returncode, stdout, stderr = await _run_git_command(["remote", "-v"], cwd)
    
    if returncode != 0:
        return []
    
    remotes = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            remotes.append({"name": parts[0], "url": parts[1]})
    return remotes
