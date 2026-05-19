from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from api_server.services.mcp import MCPService, TransportType
from api_server.middleware.auth import get_current_active_user

router = APIRouter(prefix="/mcp", tags=["mcp"])

mcp_service = MCPService()

class CreateClientRequest(BaseModel):
    transport_type: str = "stdio"
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None

class ToolCallRequest(BaseModel):
    client_id: str
    tool_name: str
    arguments: Optional[Dict[str, Any]] = None

class MessageRequest(BaseModel):
    client_id: str
    method: str
    params: Optional[Dict[str, Any]] = None

@router.post("/clients")
async def create_client(
    request: CreateClientRequest,
    current_user: dict = Depends(get_current_active_user),
):
    client_id = f"client_{current_user['id']}"
    client = mcp_service.create_client(
        client_id=client_id,
        transport_type=request.transport_type,
        command=request.command,
        args=request.args,
        url=request.url,
    )
    
    if client.connect():
        return {"client_id": client_id, "status": "connected"}
    else:
        return {"client_id": client_id, "status": "disconnected"}

@router.get("/clients/{client_id}")
async def get_client(
    client_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    client = mcp_service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {
        "client_id": client_id,
        "connected": client.is_connected(),
        "transport_type": client.transport_type.value,
    }

@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    result = mcp_service.remove_client(client_id)
    if not result:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"status": "deleted"}

@router.post("/tools/call")
async def call_tool(
    request: ToolCallRequest,
    current_user: dict = Depends(get_current_active_user),
):
    tool = mcp_service.get_tool(request.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    try:
        result = tool(**(request.arguments or {}))
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message")
async def send_message(
    request: MessageRequest,
    current_user: dict = Depends(get_current_active_user),
):
    client = mcp_service.get_client(request.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    result = client.send_message(request.method, request.params)
    return result

@router.get("/tools")
async def list_tools(
    current_user: dict = Depends(get_current_active_user),
):
    tools = mcp_service.list_tools()
    return {"tools": tools}