"""Agent SDK types and session management - bridging gap with TypeScript entrypoints/"""
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class SessionTag(Enum):
    PROJECT = "project"
    FEATURE = "feature"
    BUG = "bug"
    RESEARCH = "research"
    DOC = "documentation"


@dataclass
class CronTask:
    id: str
    cron_expression: str
    callback: Callable
    enabled: bool = True
    timeout_seconds: int = 300


@dataclass
class RemoteControlHandle:
    session_id: str
    remote_url: str
    connected: bool = False
    on_message: Optional[Callable] = None


class ForkSession:
    """
    Fork a session with isolation.
    
    TypeScript equivalent: agentSdkTypes.ts forkSession
    Python gap: No fork session.
    """
    
    def __init__(self):
        self._forked_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def fork(
        self,
        parent_session_id: str,
        name: str,
        worktree_path: Optional[str] = None
    ) -> str:
        import uuid
        fork_id = f"fork_{uuid.uuid4().hex[:8]}"
        
        self._forked_sessions[fork_id] = {
            "parent_session_id": parent_session_id,
            "name": name,
            "worktree_path": worktree_path,
            "status": "running"
        }
        
        return fork_id
    
    def get_fork(self, fork_id: str) -> Optional[Dict[str, Any]]:
        return self._forked_sessions.get(fork_id)
    
    def tag_session(self, session_id: str, tags: List[SessionTag]) -> None:
        if session_id in self._forked_sessions:
            self._forked_sessions[session_id]["tags"] = [t.value for t in tags]
    
    def rename_session(self, session_id: str, new_name: str) -> bool:
        if session_id in self._forked_sessions:
            self._forked_sessions[session_id]["name"] = new_name
            return True
        return False


class AgentSessionManager:
    """
    Central session management with fork/tag/rename.
    
    TypeScript equivalent: agentSdkTypes.ts
    Python gap: Basic session routes only.
    """
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._cron_tasks: Dict[str, CronTask] = {}
        self._remote_controls: Dict[str, RemoteControlHandle] = {}
        self._fork_session = ForkSession()
    
    def create_session(
        self,
        session_id: str,
        name: str,
        model: str = "sonnet"
    ) -> Dict[str, Any]:
        session = {
            "id": session_id,
            "name": name,
            "model": model,
            "status": "active",
            "tags": [],
            "created_at": None
        }
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)
    
    def fork_session(
        self,
        parent_session_id: str,
        name: str,
        worktree_path: Optional[str] = None
    ) -> str:
        return asyncio.create_task(
            self._fork_session.fork(parent_session_id, name, worktree_path)
        )
    
    def tag_session(self, session_id: str, tags: List[SessionTag]) -> None:
        self._fork_session.tag_session(session_id, tags)
        if session_id in self._sessions:
            self._sessions[session_id]["tags"] = [t.value for t in tags]
    
    def rename_session(self, session_id: str, new_name: str) -> bool:
        result = self._fork_session.rename_session(session_id, new_name)
        if session_id in self._sessions and result:
            self._sessions[session_id]["name"] = new_name
        return result
    
    def add_cron_task(self, task: CronTask) -> None:
        self._cron_tasks[task.id] = task
    
    def remove_cron_task(self, task_id: str) -> None:
        if task_id in self._cron_tasks:
            del self._cron_tasks[task_id]
    
    def create_remote_control(
        self,
        session_id: str,
        remote_url: str
    ) -> RemoteControlHandle:
        handle = RemoteControlHandle(
            session_id=session_id,
            remote_url=remote_url
        )
        self._remote_controls[session_id] = handle
        return handle
    
    def get_remote_control(self, session_id: str) -> Optional[RemoteControlHandle]:
        return self._remote_controls.get(session_id)


_session_manager: Optional[AgentSessionManager] = None


def get_session_manager() -> AgentSessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = AgentSessionManager()
    return _session_manager
