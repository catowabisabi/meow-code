"""Enhanced session state management - bridging gap with TypeScript sessionState.ts"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Optional
from enum import Enum
from datetime import datetime
import json


class SessionState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    REQUIRES_ACTION = "requires_action"


@dataclass
class RequiresActionDetails:
    tool_name: str
    action_description: str
    tool_use_id: str
    request_id: str
    input: Optional[Dict[str, Any]] = None


@dataclass
class SessionExternalMetadata:
    permission_mode: Optional[str] = None
    is_ultraplan_mode: bool = False
    model: Optional[str] = None
    pending_action: Optional[RequiresActionDetails] = None
    post_turn_summary: Optional[Any] = None
    task_summary: Optional[str] = None


class SessionStateMachine:
    """
    State machine for session lifecycle management.
    
    TypeScript equivalent: sessionState.ts
    Python gap: Python has no session state machine.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._state = SessionState.IDLE
        self._metadata = SessionExternalMetadata()
        self._state_listeners: List[Callable[[SessionState, Optional[RequiresActionDetails]], None]] = []
        self._metadata_listeners: List[Callable[[SessionExternalMetadata], None]] = []
        self._permission_mode_listeners: List[Callable[[str], None]] = []
    
    @property
    def state(self) -> SessionState:
        return self._state
    
    @state.setter
    def state(self, value: SessionState) -> None:
        if self._state != value:
            self._state = value
            self._notify_state_change()
    
    @property
    def metadata(self) -> SessionExternalMetadata:
        return self._metadata
    
    def add_state_listener(
        self, 
        listener: Callable[[SessionState, Optional[RequiresActionDetails]], None]
    ) -> None:
        self._state_listeners.append(listener)
    
    def add_metadata_listener(
        self, 
        listener: Callable[[SessionExternalMetadata], None]
    ) -> None:
        self._metadata_listeners.append(listener)
    
    def _notify_state_change(self) -> None:
        for listener in self._state_listeners:
            details = self._metadata.pending_action if self._state == SessionState.REQUIRES_ACTION else None
            listener(self._state, details)
    
    def _notify_metadata_change(self) -> None:
        for listener in self._metadata_listeners:
            listener(self._metadata)
    
    def set_idle(self) -> None:
        self.state = SessionState.IDLE
        self._metadata.pending_action = None
    
    def set_running(self) -> None:
        self.state = SessionState.RUNNING
    
    def set_requires_action(self, details: RequiresActionDetails) -> None:
        self._metadata.pending_action = details
        self.state = SessionState.REQUIRES_ACTION
    
    def set_permission_mode(self, mode: str) -> None:
        self._metadata.permission_mode = mode
        for listener in self._permission_mode_listeners:
            listener(mode)
        self._notify_metadata_change()
    
    def update_metadata(self, updates: Dict[str, Any]) -> None:
        if "model" in updates:
            self._metadata.model = updates["model"]
        if "is_ultraplan_mode" in updates:
            self._metadata.is_ultraplan_mode = updates["is_ultraplan_mode"]
        if "task_summary" in updates:
            self._metadata.task_summary = updates["task_summary"]
        self._notify_metadata_change()


@dataclass
class SessionStorageEntry:
    session_id: str
    state: str
    metadata: Dict[str, Any]
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str


class SessionStorage:
    """
    Session persistence with buffering and UUID deduplication.
    
    TypeScript equivalent: sessionStorage.ts
    Python gap: Python uses simple JSON files - missing buffering, UUID dedup.
    """
    
    def __init__(self, storage_dir: str = "~/.claude/sessions"):
        self.storage_dir = storage_dir
        self._buffer: Dict[str, SessionStorageEntry] = {}
        self._dirty: set = set()
    
    def put(self, entry: SessionStorageEntry) -> None:
        self._buffer[entry.session_id] = entry
        self._dirty.add(entry.session_id)
    
    def get(self, session_id: str) -> Optional[SessionStorageEntry]:
        return self._buffer.get(session_id)
    
    async def flush(self) -> None:
        for session_id in self._dirty:
            entry = self._buffer.get(session_id)
            if entry:
                await self._write_to_disk(entry)
        self._dirty.clear()
    
    async def _write_to_disk(self, entry: SessionStorageEntry) -> None:
        pass


class SessionManager:
    """
    Central session management with state machine coordination.
    
    TypeScript equivalent: createSessionStateMachine() coordination
    """
    
    def __init__(self):
        self._sessions: Dict[str, SessionStateMachine] = {}
        self._active_session: Optional[str] = None
    
    def create_session(self, session_id: str) -> SessionStateMachine:
        machine = SessionStateMachine(session_id)
        self._sessions[session_id] = machine
        return machine
    
    def get_session(self, session_id: str) -> Optional[SessionStateMachine]:
        return self._sessions.get(session_id)
    
    def set_active_session(self, session_id: str) -> None:
        self._active_session = session_id
    
    def get_active_session(self) -> Optional[SessionStateMachine]:
        if self._active_session:
            return self._sessions.get(self._active_session)
        return None
    
    def list_sessions(self) -> List[str]:
        return list(self._sessions.keys())


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
