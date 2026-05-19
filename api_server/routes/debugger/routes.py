from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from api_server.services.debugger import DebuggerService
from api_server.middleware.auth import get_current_active_user

router = APIRouter(prefix="/debugger", tags=["debugger"])

debugger_service = DebuggerService()

class StartDebuggerRequest(BaseModel):
    url: str

class AttachRequest(BaseModel):
    tab_id: str

class SetBreakpointRequest(BaseModel):
    source: str
    line: int
    condition: Optional[str] = None

class EvaluateRequest(BaseModel):
    expression: str
    frame_id: Optional[str] = None

@router.post("/start")
async def start_debugger(
    request: StartDebuggerRequest,
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.start_debugger(session_id, request.url)
    return result

@router.post("/attach")
async def attach_to_tab(
    request: AttachRequest,
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.attach_to_tab(session_id, request.tab_id)
    return result

@router.post("/breakpoint")
async def set_breakpoint(
    request: SetBreakpointRequest,
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.set_breakpoint(
        session_id, request.source, request.line, request.condition
    )
    return result

@router.delete("/breakpoint/{breakpoint_id}")
async def remove_breakpoint(
    breakpoint_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.remove_breakpoint(session_id, breakpoint_id)
    return {"success": result}

@router.post("/resume")
async def resume(
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.resume(session_id)
    return result

@router.post("/pause")
async def pause(
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.pause(session_id)
    return result

@router.post("/step/over")
async def step_over(
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.step_over(session_id)
    return result

@router.post("/step/into")
async def step_into(
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.step_into(session_id)
    return result

@router.post("/step/out")
async def step_out(
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.step_out(session_id)
    return result

@router.post("/evaluate")
async def evaluate(
    request: EvaluateRequest,
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.evaluate(session_id, request.expression, request.frame_id)
    return result

@router.get("/stack")
async def get_stack_trace(
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.get_stack_trace(session_id)
    return {"frames": result}

@router.get("/variables")
async def get_variables(
    frame_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.get_variables(session_id, frame_id)
    return {"variables": result}

@router.post("/stop")
async def stop(
    current_user: dict = Depends(get_current_active_user),
):
    session_id = f"session_{current_user['id']}"
    result = await debugger_service.stop(session_id)
    return result