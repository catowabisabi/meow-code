import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/permissions", tags=["permissions"])


class PermissionRule(BaseModel):
    id: str
    tool_name: str
    action: str
    pattern: Optional[str] = None
    created_at: float
    description: Optional[str] = None


class PermissionRuleCreate(BaseModel):
    tool_name: str
    action: str
    pattern: Optional[str] = None
    description: Optional[str] = None


class PendingPermission(BaseModel):
    id: str
    tool_name: str
    arguments: dict
    requested_at: float
    status: str = "pending"
    approved_at: Optional[float] = None
    denied_at: Optional[float] = None


class RetryResult(BaseModel):
    retried_commands: List[str]
    message: str


_permission_rules: Dict[str, PermissionRule] = {}
_pending_permissions: Dict[str, PendingPermission] = {}


@router.get("", response_model=List[PermissionRule])
async def list_permissions() -> List[PermissionRule]:
    return list(_permission_rules.values())


@router.post("", response_model=PermissionRule)
async def create_permission(rule: PermissionRuleCreate) -> PermissionRule:
    rule_id = str(uuid.uuid4())
    created_rule = PermissionRule(
        id=rule_id,
        tool_name=rule.tool_name,
        action=rule.action,
        pattern=rule.pattern,
        description=rule.description,
        created_at=datetime.now().timestamp(),
    )
    _permission_rules[rule_id] = created_rule
    return created_rule


@router.delete("/{rule_id}", response_model=Dict)
async def delete_permission(rule_id: str) -> Dict:
    if rule_id in _permission_rules:
        del _permission_rules[rule_id]
        return {"status": "deleted", "id": rule_id}
    return {"status": "not_found", "id": rule_id}


@router.get("/pending", response_model=List[PendingPermission])
async def get_pending_permissions() -> List[PendingPermission]:
    return [p for p in _pending_permissions.values() if p.status == "pending"]


@router.post("/approve", response_model=PendingPermission)
async def approve_permission(permission_id: str) -> PendingPermission:
    if permission_id not in _pending_permissions:
        raise HTTPException(status_code=404, detail=f"Permission '{permission_id}' not found")
    perm = _pending_permissions[permission_id]
    perm.status = "approved"
    perm.approved_at = datetime.now().timestamp()
    return perm


@router.post("/deny", response_model=PendingPermission)
async def deny_permission(permission_id: str) -> PendingPermission:
    if permission_id not in _pending_permissions:
        raise HTTPException(status_code=404, detail=f"Permission '{permission_id}' not found")
    perm = _pending_permissions[permission_id]
    perm.status = "denied"
    perm.denied_at = datetime.now().timestamp()
    return perm


@router.get("/retry", response_model=RetryResult)
async def retry_denied_tools(commands: List[str]) -> RetryResult:
    return RetryResult(
        retried_commands=commands,
        message="Please retry the denied tools with modified input.",
    )
