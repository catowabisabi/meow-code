from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from api_server.middleware.auth import get_current_active_user
from api_server.db import get_db
from api_server.db.repositories.hook import HookRepository, HookExecutionRepository
from api_server.services.hooks import get_hook_service

router = APIRouter(prefix="/hooks", tags=["hooks"])

class HookCreate(BaseModel):
    name: str
    trigger_type: str
    hook_type: str
    config: Optional[Dict[str, Any]] = None
    code: Optional[str] = None

class HookUpdate(BaseModel):
    name: Optional[str] = None
    trigger_type: Optional[str] = None
    hook_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None

class HookResponse(BaseModel):
    id: str
    name: str
    trigger_type: str
    hook_type: str
    config: Dict[str, Any]
    code: Optional[str]
    is_active: bool
    user_id: str
    created_at: str
    updated_at: str

class ExecutionResponse(BaseModel):
    id: str
    hook_id: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_ms: Optional[int]
    error_message: Optional[str]
    result: Optional[str]

async def get_hook_repo(db: AsyncSession = Depends(get_db)) -> HookRepository:
    return HookRepository(db)

async def get_execution_repo(db: AsyncSession = Depends(get_db)) -> HookExecutionRepository:
    return HookExecutionRepository(db)

@router.get("/", response_model=List[HookResponse])
async def list_hooks(
    current_user: dict = Depends(get_current_active_user),
    repo: HookRepository = Depends(get_hook_repo),
):
    hooks = await repo.get_all(user_id=current_user["id"])
    return [HookResponse(**h) for h in hooks]

@router.post("/", response_model=HookResponse, status_code=status.HTTP_201_CREATED)
async def create_hook(
    request: HookCreate,
    current_user: dict = Depends(get_current_active_user),
    repo: HookRepository = Depends(get_hook_repo),
):
    hook = await repo.create(
        name=request.name,
        trigger_type=request.trigger_type,
        hook_type=request.hook_type,
        config=request.config,
        code=request.code,
        user_id=current_user["id"],
        is_active=True,
    )
    return HookResponse(**hook)

@router.get("/{hook_id}", response_model=HookResponse)
async def get_hook(
    hook_id: str,
    current_user: dict = Depends(get_current_active_user),
    repo: HookRepository = Depends(get_hook_repo),
):
    hook = await repo.get_by_id(hook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Hook not found")
    if hook["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return HookResponse(**hook)

@router.put("/{hook_id}", response_model=HookResponse)
async def update_hook(
    hook_id: str,
    request: HookUpdate,
    current_user: dict = Depends(get_current_active_user),
    repo: HookRepository = Depends(get_hook_repo),
):
    hook = await repo.get_by_id(hook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Hook not found")
    if hook["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    updated = await repo.update(hook_id, **update_data)
    return HookResponse(**updated)

@router.delete("/{hook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hook(
    hook_id: str,
    current_user: dict = Depends(get_current_active_user),
    repo: HookRepository = Depends(get_hook_repo),
):
    hook = await repo.get_by_id(hook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Hook not found")
    if hook["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await repo.delete(hook_id)
    return None

@router.post("/{hook_id}/execute", response_model=ExecutionResponse)
async def execute_hook(
    hook_id: str,
    payload: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_active_user),
    repo: HookRepository = Depends(get_hook_repo),
    execution_repo: HookExecutionRepository = Depends(get_execution_repo),
):
    hook = await repo.get_by_id(hook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Hook not found")
    if hook["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    hook_service = get_hook_service()

    execution = await execution_repo.create(
        hook_id=hook_id,
        status="running",
    )

    try:
        handler_code = hook.get("code")
        if handler_code:
            local_vars = {}
            exec(handler_code, {}, local_vars)
            handler = local_vars.get("handler")
            if handler:
                hook_service.register_handler(hook_id, handler)

        trigger_type = hook["trigger_type"]
        result = None

        if trigger_type == "pre":
            result = await hook_service.execute_pre_hook(
                hook_id, trigger_type, payload or {}, current_user["id"]
            )
        elif trigger_type == "post":
            result = await hook_service.execute_post_hook(
                hook_id, trigger_type, payload or {}, current_user["id"]
            )

        await execution_repo.update(
            execution["id"],
            status="completed",
            result=result,
        )
        execution = await execution_repo.get_by_id(execution["id"])
        return ExecutionResponse(**execution)
    except Exception as e:
        await execution_repo.update(
            execution["id"],
            status="failed",
            error_message=str(e),
        )
        execution = await execution_repo.get_by_id(execution["id"])
        return ExecutionResponse(**execution)

@router.get("/{hook_id}/executions", response_model=List[ExecutionResponse])
async def get_hook_executions(
    hook_id: str,
    current_user: dict = Depends(get_current_active_user),
    repo: HookRepository = Depends(get_hook_repo),
    execution_repo: HookExecutionRepository = Depends(get_execution_repo),
):
    hook = await repo.get_by_id(hook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Hook not found")
    if hook["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    executions = await execution_repo.get_by_hook_id(hook_id)
    return [ExecutionResponse(**e) for e in executions]

@router.get("/executions", response_model=List[ExecutionResponse])
async def get_all_executions(
    current_user: dict = Depends(get_current_active_user),
    repo: HookRepository = Depends(get_hook_repo),
    execution_repo: HookExecutionRepository = Depends(get_execution_repo),
):
    hooks = await repo.get_all(user_id=current_user["id"])
    all_executions = []
    for hook in hooks:
        executions = await execution_repo.get_by_hook_id(hook["id"])
        all_executions.extend(executions)
    return [ExecutionResponse(**e) for e in all_executions]