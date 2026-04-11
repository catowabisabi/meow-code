from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from api_server.tools import get_all_tools

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolInfo(BaseModel):
    name: str
    description: str
    isReadOnly: bool = False
    riskLevel: str = "low"
    inputSchema: dict = {}


class ToolsResponse(BaseModel):
    tools: List[ToolInfo]
    count: int


@router.get("", response_model=ToolsResponse)
async def list_tools() -> ToolsResponse:
    try:
        all_tools = get_all_tools()
        tools = [
            ToolInfo(
                name=t.name,
                description=t.description,
                isReadOnly=getattr(t, 'is_read_only', False),
                riskLevel=getattr(t, 'risk_level', 'low'),
                inputSchema=getattr(t, 'input_schema', {}),
            )
            for t in all_tools
        ]
        return ToolsResponse(tools=tools, count=len(tools))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading tools: {str(e)}")
