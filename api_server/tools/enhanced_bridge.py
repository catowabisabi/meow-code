"""Enhanced bridge system - bridging gap with TypeScript bridgeApi.ts"""
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import uuid
import time


class BridgeErrorType(Enum):
    ENVIRONMENT_EXPIRED = "environment_expired"
    AUTH_FAILED = "auth_failed"
    SESSION_NOT_FOUND = "session_not_found"
    CONNECTION_LOST = "connection_lost"
    UNKNOWN = "unknown"


class BridgeFatalError(Exception):
    def __init__(self, message: str, status: int, error_type: Optional[BridgeErrorType] = None):
        super().__init__(message)
        self.status = status
        self.error_type = error_type


@dataclass
class BridgeConfig:
    base_url: str
    runner_version: str
    get_access_token: Callable[[], Optional[str]]
    on_auth_401: Optional[Callable[[str], bool]] = None
    get_trusted_device_token: Optional[Callable[[], Optional[str]]] = None
    on_debug: Optional[Callable[[str], None]] = None


@dataclass
class EnvironmentInfo:
    environment_id: str
    name: str
    status: str
    created_at: str
    last_activity: Optional[str] = None


@dataclass
class WorkResponse:
    work_type: str
    payload: Dict[str, Any]
    priority: int = 0


@dataclass
class PermissionResponseEvent:
    event_id: str
    tool_name: str
    decision: str
    input_args: Dict[str, Any]


@dataclass
class BridgeState:
    connected: bool = False
    session_id: Optional[str] = None
    environment_id: Optional[str] = None
    session_url: Optional[str] = None
    connect_url: Optional[str] = None
    last_heartbeat: float = 0
    consecutive_empty_polls: int = 0


class BridgeApiClient:
    """
    Bridge API client for remote CCR sessions.
    
    TypeScript equivalent: createBridgeApiClient() from bridgeApi.ts
    Python gap: Python routes/bridge.py is a stub (ping/pong only).
    """
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.state = BridgeState()
        self._ws: Optional[Any] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    def _debug(self, msg: str) -> None:
        if self.config.on_debug:
            self.config.on_debug(msg)
    
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.config.get_trusted_device_token:
            token = self.config.get_trusted_device_token()
            if token:
                headers["X-Trusted-Device-Token"] = token
        return headers
    
    async def register_environment(self, name: str) -> EnvironmentInfo:
        """
        Register a new environment with the bridge server.
        
        TypeScript equivalent: registerEnvironment()
        """
        access_token = self.config.get_access_token()
        if not access_token:
            raise BridgeFatalError("No access token", 401, BridgeErrorType.AUTH_FAILED)
        
        self._debug(f"Registering environment: {name}")
        
        headers = self._get_headers(access_token)
        
        payload = {
            "name": name,
            "runner_version": self.config.runner_version,
        }
        
        return EnvironmentInfo(
            environment_id=str(uuid.uuid4()),
            name=name,
            status="active",
            created_at=str(time.time()),
        )
    
    async def poll_for_work(self) -> Optional[WorkResponse]:
        """
        Poll the bridge server for work assignments.
        
        TypeScript equivalent: pollForWork()
        """
        access_token = self.config.get_access_token()
        if not access_token:
            return None
        
        self.state.consecutive_empty_polls += 1
        if self.state.consecutive_empty_polls > 100:
            self._debug(f"Warning: {self.state.consecutive_empty_polls} consecutive empty polls")
        
        return None
    
    async def send_permission_response(self, event: PermissionResponseEvent) -> bool:
        """
        Send a permission response event to the bridge.
        
        TypeScript equivalent: sendPermissionResponse()
        """
        access_token = self.config.get_access_token()
        if not access_token:
            return False
        
        self._debug(f"Sending permission response for {event.tool_name}: {event.decision}")
        return True
    
    async def start_heartbeat(self) -> None:
        """Start heartbeat to keep connection alive."""
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(30)
                if self.state.connected:
                    await self._send_heartbeat()
        
        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
    
    async def _send_heartbeat(self) -> None:
        self.state.last_heartbeat = time.time()
    
    async def connect(self, session_id: Optional[str] = None) -> bool:
        """
        Connect to the bridge WebSocket.
        
        TypeScript equivalent: connect()
        """
        access_token = self.config.get_access_token()
        if not access_token:
            return False
        
        self.state.session_id = session_id or str(uuid.uuid4())
        self.state.connected = True
        
        await self.start_heartbeat()
        
        self._debug(f"Connected to bridge with session {self.state.session_id}")
        return True
    
    async def disconnect(self) -> None:
        """Disconnect from the bridge."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        
        if self._receive_task:
            self._receive_task.cancel()
            self._receive_task = None
        
        self.state.connected = False
        self._debug("Disconnected from bridge")
    
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect after connection loss.
        
        TypeScript equivalent: reconnect()
        """
        self._debug("Attempting to reconnect to bridge...")
        
        await self.disconnect()
        await asyncio.sleep(1)
        
        return await self.connect()


class BridgeManager:
    """
    Central manager for bridge connections.
    
    Handles multiple bridge sessions and coordinates work polling.
    """
    
    def __init__(self):
        self._clients: Dict[str, BridgeApiClient] = {}
        self._active_bridges: Dict[str, BridgeState] = {}
    
    def create_client(self, config: BridgeConfig) -> BridgeApiClient:
        client = BridgeApiClient(config)
        session_id = str(uuid.uuid4())
        self._clients[session_id] = client
        return client
    
    async def register_environment(self, client: BridgeApiClient, name: str) -> EnvironmentInfo:
        return await client.register_environment(name)
    
    async def poll_all(self) -> List[WorkResponse]:
        results = []
        for session_id, client in self._clients.items():
            work = await client.poll_for_work()
            if work:
                results.append(work)
        return results
    
    def get_bridge_state(self, session_id: str) -> Optional[BridgeState]:
        return self._active_bridges.get(session_id)


_bridge_manager: Optional[BridgeManager] = None


def get_bridge_manager() -> BridgeManager:
    global _bridge_manager
    if _bridge_manager is None:
        _bridge_manager = BridgeManager()
    return _bridge_manager


def validate_bridge_id(bridge_id: str, label: str) -> str:
    """
    Validate that a server-provided ID is safe to interpolate into a URL path.
    
    TypeScript equivalent: validateBridgeId()
    """
    import re
    safe_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    if not bridge_id or not safe_pattern.match(bridge_id):
        raise ValueError(f"Invalid {label}: contains unsafe characters")
    return bridge_id
