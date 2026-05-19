import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from websockets.client import connect

class DebuggerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"

@dataclass
class Breakpoint:
    id: str
    source: str
    line: int
    condition: Optional[str] = None
    enabled: bool = True

@dataclass
class StackFrame:
    id: str
    name: str
    source: str
    line: int
    column: int

@dataclass
class Variable:
    name: str
    value: str
    type: str

@dataclass
class DebugSession:
    id: str
    websocket: Any
    state: DebuggerState = DebuggerState.IDLE
    breakpoints: List[Breakpoint] = field(default_factory=list)
    current_frame: Optional[StackFrame] = None
    variables: List[Variable] = field(default_factory=list)
    paused_reason: Optional[str] = None

class DebuggerService:
    def __init__(self):
        self.sessions: Dict[str, DebugSession] = {}
        self.chrome_port = 9222

    async def start_debugger(self, session_id: str, url: str) -> Dict[str, Any]:
        ws_url = f"ws://localhost:{self.chrome_port}/devtools/browser"
        try:
            ws = await connect(ws_url)
            session = DebugSession(id=session_id, websocket=ws)
            self.sessions[session_id] = session
            return {"session_id": session_id, "status": "connected"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    async def attach_to_tab(self, session_id: str, tab_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        ws_url = f"ws://localhost:{self.chrome_port}/devtools/page/{tab_id}"

        try:
            ws = await connect(ws_url)
            session.websocket = ws
            await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
            await ws.send(json.dumps({"id": 2, "method": "Debugger.enable"}))
            return {"status": "attached", "tab_id": tab_id}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    async def set_breakpoint(
        self,
        session_id: str,
        source: str,
        line: int,
        condition: Optional[str] = None,
    ) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        breakpoint = Breakpoint(
            id=f"bp_{len(session.breakpoints)}",
            source=source,
            line=line,
            condition=condition,
        )
        session.breakpoints.append(breakpoint)

        command = {
            "id": 10,
            "method": "Debugger.setBreakpoint",
            "params": {
                "location": {"scriptId": source, "lineNumber": line},
                "condition": condition,
            },
        }
        await session.websocket.send(json.dumps(command))

        return {"breakpoint_id": breakpoint.id, "line": line}

    async def remove_breakpoint(self, session_id: str, breakpoint_id: str) -> bool:
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session.breakpoints = [bp for bp in session.breakpoints if bp.id != breakpoint_id]
        return True

    async def resume(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        command = {"id": 20, "method": "Debugger.resume"}
        await session.websocket.send(json.dumps(command))
        session.state = DebuggerState.RUNNING
        return {"status": "resumed"}

    async def pause(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        command = {"id": 21, "method": "Debugger.pause"}
        await session.websocket.send(json.dumps(command))
        session.state = DebuggerState.PAUSED
        return {"status": "paused"}

    async def step_over(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        command = {"id": 22, "method": "Debugger.stepOver"}
        await session.websocket.send(json.dumps(command))
        return {"status": "stepping"}

    async def step_into(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        command = {"id": 23, "method": "Debugger.stepInto"}
        await session.websocket.send(json.dumps(command))
        return {"status": "stepping"}

    async def step_out(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        command = {"id": 24, "method": "Debugger.stepOut"}
        await session.websocket.send(json.dumps(command))
        return {"status": "stepping"}

    async def evaluate(
        self,
        session_id: str,
        expression: str,
        frame_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        params = {"expression": expression, "returnByValue": True}
        if frame_id:
            params["executionContextId"] = frame_id

        command = {"id": 30, "method": "Runtime.evaluate", "params": params}
        await session.websocket.send(json.dumps(command))

        return {"status": "evaluated", "expression": expression}

    async def get_stack_trace(self, session_id: str) -> List[Dict[str, Any]]:
        if session_id not in self.sessions:
            return []

        session = self.sessions[session_id]
        if not session.current_frame:
            return []

        return [{
            "id": session.current_frame.id,
            "name": session.current_frame.name,
            "source": session.current_frame.source,
            "line": session.current_frame.line,
            "column": session.current_frame.column,
        }]

    async def get_variables(self, session_id: str, frame_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if session_id not in self.sessions:
            return []

        session = self.sessions[session_id]
        return [
            {"name": v.name, "value": v.value, "type": v.type}
            for v in session.variables
        ]

    async def stop(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        await session.websocket.close()
        del self.sessions[session_id]
        return {"status": "stopped"}

    def get_session(self, session_id: str) -> Optional[DebugSession]:
        return self.sessions.get(session_id)

    def list_sessions(self) -> List[str]:
        return list(self.sessions.keys())