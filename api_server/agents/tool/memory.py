"""
Agent memory management for persistent context across agent sessions.

Provides memory context creation, retrieval, and snapshotting for resume functionality.
Supports 'user' (~/.claude/agent-memory/), 'project' (.claude/agent-memory/),
and 'local' (.claude/agent-memory-local/) scopes.
"""
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class AgentMemoryScope(Enum):
    """Scope for agent memory persistence."""
    USER = "user"
    PROJECT = "project"
    LOCAL = "local"


AGENT_MEMORY_DIR = ".claude/agent-memory"
AGENT_MEMORY_LOCAL_DIR = ".claude/agent-memory-local"


def _sanitize_agent_type_for_path(agent_type: str) -> str:
    """Sanitize agent type name for use as directory name.
    
    Replaces colons (invalid on Windows, used in plugin-namespaced
    agent types like "my-plugin:my-agent") with dashes.
    """
    return agent_type.replace(":", "-")


def _get_cwd() -> str:
    """Get current working directory."""
    return os.getcwd()


def _get_memory_base_dir() -> str:
    """Get base memory directory (user's Claude config dir)."""
    return os.path.expanduser("~/.claude")


def _get_local_agent_memory_dir(dir_name: str) -> str:
    """Get local agent memory directory (project-specific, not in VCS).
    
    When CLAUDE_CODE_REMOTE_MEMORY_DIR is set, persists to the mount
    with project namespacing. Otherwise uses <cwd>/.claude/agent-memory-local/<agentType>/.
    """
    remote_dir = os.environ.get("CLAUDE_CODE_REMOTE_MEMORY_DIR")
    if remote_dir:
        return os.path.join(
            remote_dir,
            "projects",
            _get_cwd(),
            "agent-memory-local",
            dir_name,
        )
    return os.path.join(_get_cwd(), AGENT_MEMORY_LOCAL_DIR, dir_name)


def get_agent_memory_dir(
    agent_type: str,
    scope: AgentMemoryScope,
) -> str:
    """Get the agent memory directory for a given agent type and scope.
    
    - 'user' scope: <memoryBase>/agent-memory/<agentType>/
    - 'project' scope: <cwd>/.claude/agent-memory/<agentType>/
    - 'local' scope: see getLocalAgentMemoryDir()
    """
    dir_name = _sanitize_agent_type_for_path(agent_type)
    
    if scope == AgentMemoryScope.PROJECT:
        return os.path.join(_get_cwd(), AGENT_MEMORY_DIR, dir_name)
    elif scope == AgentMemoryScope.LOCAL:
        return _get_local_agent_memory_dir(dir_name)
    elif scope == AgentMemoryScope.USER:
        return os.path.join(_get_memory_base_dir(), "agent-memory", dir_name)
    else:
        return os.path.join(_get_cwd(), AGENT_MEMORY_DIR, dir_name)


def get_agent_memory_entrypoint(
    agent_type: str,
    scope: AgentMemoryScope,
) -> str:
    """Get the agent memory file path for a given agent type and scope."""
    return os.path.join(
        get_agent_memory_dir(agent_type, scope),
        "MEMORY.md",
    )


def is_agent_memory_path(absolute_path: str) -> bool:
    """Check if file is within an agent memory directory (any scope).
    
    SECURITY: Normalizes path to prevent traversal bypasses via .. segments.
    """
    path = Path(absolute_path).resolve()
    
    memory_base = Path(_get_memory_base_dir()).resolve()
    cwd = Path(_get_cwd()).resolve()
    
    user_scope = path.is_relative_to(memory_base / "agent-memory")
    if user_scope:
        return True
    
    project_scope = path.is_relative_to(cwd / AGENT_MEMORY_DIR)
    if project_scope:
        return True
    
    remote_dir = os.environ.get("CLAUDE_CODE_REMOTE_MEMORY_DIR")
    if remote_dir:
        remote_path = Path(remote_dir).resolve()
        if path.is_relative_to(remote_path / "projects"):
            return True
    else:
        local_scope = path.is_relative_to(cwd / AGENT_MEMORY_LOCAL_DIR)
        if local_scope:
            return True
    
    return False


def get_memory_scope_display(scope: Optional[AgentMemoryScope]) -> str:
    """Get human-readable display string for memory scope."""
    if scope == AgentMemoryScope.USER:
        return f"User ({os.path.join(_get_memory_base_dir(), 'agent-memory')}/)"
    elif scope == AgentMemoryScope.PROJECT:
        return "Project (.claude/agent-memory/)"
    elif scope == AgentMemoryScope.LOCAL:
        return f"Local ({_get_local_agent_memory_dir('...')})"
    else:
        return "None"


@dataclass
class AgentMemoryContext:
    """Context for agent memory operations."""
    agent_type: str
    scope: AgentMemoryScope
    memory_dir: str
    memory_file: str
    exists: bool


def create_agent_memory(
    agent_type: str,
    scope: AgentMemoryScope,
) -> AgentMemoryContext:
    """Create agent memory context and ensure directory exists.
    
    Creates the memory directory if needed.
    Returns context with memory location and existence status.
    """
    memory_dir = get_agent_memory_dir(agent_type, scope)
    memory_file = get_agent_memory_entrypoint(agent_type, scope)
    
    try:
        Path(memory_dir).mkdir(parents=True, exist_ok=True)
        exists = Path(memory_file).exists()
    except OSError:
        exists = False
    
    return AgentMemoryContext(
        agent_type=agent_type,
        scope=scope,
        memory_dir=memory_dir,
        memory_file=memory_file,
        exists=exists,
    )


def get_agent_memory(
    agent_type: str,
    scope: AgentMemoryScope,
) -> Optional[str]:
    """Retrieve agent memory contents for a given agent type and scope.
    
    Returns memory file contents if memory file exists, None otherwise.
    """
    memory_file = get_agent_memory_entrypoint(agent_type, scope)
    
    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, IOError):
        return None


def snapshot_agent_memory(
    agent_type: str,
    scope: AgentMemoryScope,
) -> dict:
    """Create a snapshot of agent memory for resume functionality.
    
    Returns a dict with memory contents and metadata for reconstruction
    when resuming an agent.
    """
    memory_file = get_agent_memory_entrypoint(agent_type, scope)
    memory_dir = get_agent_memory_dir(agent_type, scope)
    
    contents = None
    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            contents = f.read()
    except (FileNotFoundError, PermissionError, IOError):
        pass
    
    return {
        "agent_type": agent_type,
        "scope": scope.value,
        "memory_dir": memory_dir,
        "memory_file": memory_file,
        "exists": contents is not None,
        "contents": contents,
    }


def build_memory_prompt(
    agent_type: str,
    scope: AgentMemoryScope,
    extra_guidelines: Optional[list[str]] = None,
) -> str:
    """Build a prompt string with memory contents for agent context.
    
    Returns a formatted prompt that includes memory guidelines and contents.
    """
    memory_file = get_agent_memory_entrypoint(agent_type, scope)
    memory_dir = get_agent_memory_dir(agent_type, scope)
    
    scope_notes = {
        AgentMemoryScope.USER: (
            "- Since this memory is user-scope, keep learnings general "
            "since they apply across all projects"
        ),
        AgentMemoryScope.PROJECT: (
            "- Since this memory is project-scope and shared with your team "
            "via version control, tailor your memories to this project"
        ),
        AgentMemoryScope.LOCAL: (
            "- Since this memory is local-scope (not checked into version control), "
            "tailor your memories to this project and machine"
        ),
    }
    
    guidelines = [scope_notes.get(scope, "")]
    
    cowork_extra = os.environ.get("CLAUDE_COWORK_MEMORY_EXTRA_GUIDELINES")
    if cowork_extra and cowork_extra.strip():
        guidelines.append(cowork_extra.strip())
    
    if extra_guidelines:
        guidelines.extend(extra_guidelines)
    
    try:
        Path(memory_dir).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    
    guidelines_text = "\n".join(f"  {g}" for g in guidelines if g)
    
    return f"""Persistent Agent Memory: {memory_file}

{guidelines_text}
"""
