from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from api_server.services.lsp import LSPService
from api_server.middleware.auth import get_current_active_user

router = APIRouter(prefix="/lsp", tags=["lsp"])

lsp_service = LSPService()

class InitializeRequest(BaseModel):
    language: str
    root_uri: Optional[str] = None

class CompletionRequest(BaseModel):
    language: str
    file_path: str
    position: Dict[str, int]
    content: str

class HoverRequest(BaseModel):
    language: str
    file_path: str
    position: Dict[str, int]

class DefinitionRequest(BaseModel):
    language: str
    file_path: str
    position: Dict[str, int]

@router.post("/initialize")
async def initialize_server(
    request: InitializeRequest,
    current_user: dict = Depends(get_current_active_user),
):
    try:
        result = await lsp_service.initialize_server(request.language, request.root_uri)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/completions")
async def get_completions(
    request: CompletionRequest,
    current_user: dict = Depends(get_current_active_user),
):
    result = await lsp_service.get_completions(
        request.language,
        request.file_path,
        request.position,
        request.content,
    )
    return {"items": result}

@router.post("/hover")
async def get_hover(
    request: HoverRequest,
    current_user: dict = Depends(get_current_active_user),
):
    result = await lsp_service.getHover(
        request.language,
        request.file_path,
        request.position,
    )
    return result or {"contents": ""}

@router.post("/definition")
async def get_definition(
    request: DefinitionRequest,
    current_user: dict = Depends(get_current_active_user),
):
    result = await lsp_service.get_definition(
        request.language,
        request.file_path,
        request.position,
    )
    return {"locations": result or []}

@router.post("/shutdown")
async def shutdown_server(
    language: str,
    current_user: dict = Depends(get_current_active_user),
):
    await lsp_service.shutdown_server(language)
    return {"status": "shutdown"}