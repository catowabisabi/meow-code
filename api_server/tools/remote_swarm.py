"""Remote session and Swarm - bridging gap with TypeScript hooks/, utils/swarm/"""
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum
import websockets


logger = logging.getLogger(__name__)


class RemoteSessionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class RemoteSessionHandle:
    session_id: str
    websocket_url: str
    state: RemoteSessionState
    on_message: Optional[Callable] = None
    on_error: Optional[Callable] = None


class RemoteSession:
    """
    Remote CCR session.
    
    TypeScript equivalent: hooks/useRemoteSession.ts
    Python gap: No remote CCR session.
    """
    
    def __init__(self):
        self._sessions: Dict[str, RemoteSessionHandle] = {}
        self._active_session: Optional[str] = None
    
    async def connect(
        self,
        session_id: str,
        websocket_url: str,
        on_message: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> RemoteSessionHandle:
        handle = RemoteSessionHandle(
            session_id=session_id,
            websocket_url=websocket_url,
            state=RemoteSessionState.CONNECTING,
            on_message=on_message,
            on_error=on_error
        )
        
        self._sessions[session_id] = handle
        
        try:
            ws = await websockets.connect(websocket_url)
            handle.state = RemoteSessionState.CONNECTED
            self._active_session = session_id
            
            asyncio.create_task(self._receive_loop(session_id, ws))
            
            return handle
        
        except Exception as e:
            handle.state = RemoteSessionState.ERROR
            if handle.on_error:
                handle.on_error(e)
            return handle
    
    async def _receive_loop(self, session_id: str, ws) -> None:
        handle = self._sessions.get(session_id)
        if not handle:
            return
        
        try:
            async for message in ws:
                if handle.on_message:
                    handle.on_message(message)
        
        except websockets.ConnectionClosed:
            handle.state = RemoteSessionState.DISCONNECTED
        except Exception as e:
            handle.state = RemoteSessionState.ERROR
            if handle.on_error:
                handle.on_error(e)
    
    async def send_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        handle = self._sessions.get(session_id)
        if not handle or handle.state != RemoteSessionState.CONNECTED:
            return False
        
        try:
            await handle.websocket.send(str(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def disconnect(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]
        
        if self._active_session == session_id:
            self._active_session = None
    
    def get_session(self, session_id: str) -> Optional[RemoteSessionHandle]:
        return self._sessions.get(session_id)
    
    def get_active_session(self) -> Optional[str]:
        return self._active_session


class SwarmCoordinator:
    """
    Swarm coordination for multi-agent.
    
    TypeScript equivalent: utils/swarm/inProcessRunner.ts
    Python gap: No in-process execution.
    """
    
    def __init__(self):
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._leader_id: Optional[str] = None
        self._permission_bridges: Dict[str, Any] = {}
    
    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        is_leader: bool = False
    ) -> None:
        self._agents[agent_id] = {
            "id": agent_id,
            "type": agent_type,
            "is_leader": is_leader,
            "status": "running"
        }
        
        if is_leader:
            self._leader_id = agent_id
    
    async def unregister_agent(self, agent_id: str) -> None:
        if agent_id in self._agents:
            del self._agents[agent_id]
        
        if self._leader_id == agent_id:
            self._leader_id = None
    
    def get_leader_id(self) -> Optional[str]:
        return self._leader_id
    
    def get_agents(self) -> List[Dict[str, Any]]:
        return list(self._agents.values())
    
    async def sync_permissions(self, agent_id: str, permissions: Dict[str, Any]) -> bool:
        self._permission_bridges[agent_id] = permissions
        
        for other_id, other_perms in self._permission_bridges.items():
            if other_id != agent_id:
                pass
        
        return True


class LeaderPermissionBridge:
    """
    Permission bridge for in-process teammates.
    
    TypeScript equivalent: utils/swarm/leaderPermissionBridge.ts
    Python gap: No permission bridge.
    """
    
    def __init__(self):
        self._permissions: Dict[str, Any] = {}
    
    def set_permissions(self, permissions: Dict[str, Any]) -> None:
        self._permissions = permissions
    
    def get_permissions(self, agent_id: str) -> Dict[str, Any]:
        return self._permissions
    
    def has_permission(self, agent_id: str, permission: str) -> bool:
        return permission in self._permissions.get(agent_id, [])


_remote_session: Optional[RemoteSession] = None
_swarm_coordinator: Optional[SwarmCoordinator] = None


def get_remote_session() -> RemoteSession:
    global _remote_session
    if _remote_session is None:
        _remote_session = RemoteSession()
    return _remote_session


def get_swarm_coordinator() -> SwarmCoordinator:
    global _swarm_coordinator
    if _swarm_coordinator is None:
        _swarm_coordinator = SwarmCoordinator()
    return _swarm_coordinator
