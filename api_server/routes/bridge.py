"""
FastAPI routes for bidirectional remote bridge sessions.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import uuid

router = APIRouter(prefix="/bridge", tags=["bridge"])


class BridgeState(BaseModel):
    enabled: bool = False
    connected: bool = False
    session_url: Optional[str] = None
    connect_url: Optional[str] = None
    outbound_only: bool = False
    session_id: Optional[str] = None


_bridge_state: BridgeState = BridgeState()
_bridge_clients: Dict[str, list[WebSocket]] = {}
_state_lock: asyncio.Lock = asyncio.Lock()


class BridgeStatus(BaseModel):
    connected: bool
    session_url: Optional[str]
    connect_url: Optional[str]
    outbound_only: bool


class BridgeConnectResponse(BaseModel):
    success: bool
    session_url: Optional[str]
    message: str


class BridgeMessage(BaseModel):
    type: str
    payload: Optional[Dict[str, Any]] = None


@router.get("/status", response_model=BridgeStatus)
async def get_bridge_status() -> BridgeStatus:
    return BridgeStatus(
        connected=_bridge_state.connected,
        session_url=_bridge_state.session_url,
        connect_url=_bridge_state.connect_url,
        outbound_only=_bridge_state.outbound_only,
    )


@router.post("/connect", response_model=BridgeConnectResponse)
async def connect_bridge(name: Optional[str] = None) -> BridgeConnectResponse:
    async with _state_lock:
        if _bridge_state.connected:
            return BridgeConnectResponse(
                success=True,
                session_url=_bridge_state.session_url,
                message="Bridge already connected"
            )
        
        session_id = str(uuid.uuid4())
        
        _bridge_state.enabled = True
        _bridge_state.connected = True
        _bridge_state.session_id = session_id
        _bridge_state.session_url = f"/ws/bridge/{session_id}"
        _bridge_state.connect_url = f"/bridge/connect?session={session_id}"
        _bridge_state.outbound_only = False
        
        _bridge_clients[session_id] = []
        
        return BridgeConnectResponse(
            success=True,
            session_url=_bridge_state.session_url,
            message=f"Bridge connected successfully with session {session_id}"
        )


@router.delete("/disconnect")
async def disconnect_bridge() -> Dict[str, Any]:
    async with _state_lock:
        if not _bridge_state.connected:
            return {
                "success": False,
                "message": "Bridge not connected"
            }
        
        session_id = _bridge_state.session_id
        
        if session_id and session_id in _bridge_clients:
            for client in _bridge_clients[session_id]:
                try:
                    await client.close()
                except Exception:
                    pass
            del _bridge_clients[session_id]
        
        _bridge_state.enabled = False
        _bridge_state.connected = False
        _bridge_state.session_url = None
        _bridge_state.connect_url = None
        _bridge_state.outbound_only = False
        _bridge_state.session_id = None
        
        return {
            "success": True,
            "message": "Bridge disconnected successfully"
        }


async def bridge_websocket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    
    async with _state_lock:
        if session_id not in _bridge_clients:
            _bridge_clients[session_id] = []
        _bridge_clients[session_id].append(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Bridge WebSocket connected"
        })
        
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )
                
                msg_type = data.get("type", "unknown")
                
                if msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": data.get("timestamp")
                    })
                    
                elif msg_type == "status":
                    await websocket.send_json({
                        "type": "status",
                        "payload": {
                            "connected": _bridge_state.connected,
                            "session_url": _bridge_state.session_url,
                            "connect_url": _bridge_state.connect_url,
                            "outbound_only": _bridge_state.outbound_only,
                        }
                    })
                    
                elif msg_type == "command":
                    command = data.get("command", "")
                    payload = data.get("payload", {})
                    
                    await broadcast_to_session(
                        session_id,
                        {
                            "type": "command",
                            "command": command,
                            "payload": payload,
                            "from_client": True
                        },
                        exclude=websocket
                    )
                    
                elif msg_type == "message":
                    await broadcast_to_session(
                        session_id,
                        {
                            "type": "message",
                            "payload": data.get("payload", {}),
                        },
                        exclude=None
                    )
                    
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}"
                    })
                    
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": str(uuid.uuid4())
                    })
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
    finally:
        async with _state_lock:
            if session_id in _bridge_clients:
                if websocket in _bridge_clients[session_id]:
                    _bridge_clients[session_id].remove(websocket)
                if not _bridge_clients[session_id]:
                    del _bridge_clients[session_id]


async def broadcast_to_session(
    session_id: str,
    message: Dict[str, Any],
    exclude: Optional[WebSocket] = None
) -> None:
    if session_id not in _bridge_clients:
        return
        
    disconnected = []
    for client in _bridge_clients[session_id]:
        if client is exclude:
            continue
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)
    
    if disconnected:
        async with _state_lock:
            for client in disconnected:
                if client in _bridge_clients.get(session_id, []):
                    _bridge_clients[session_id].remove(client)
