from fastapi import APIRouter, Depends, HTTPException, status
from api_server.middleware.auth import get_current_active_user, require_admin

router = APIRouter(prefix="/departments", tags=["departments"])

@router.get("")
async def list_departments(
    current_user: dict = Depends(get_current_active_user),
):
    return []

@router.get("/{department_id}")
async def get_department(
    department_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    raise HTTPException(status_code=404, detail="Department not found")

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_department(
    data: dict,
    current_user: dict = Depends(require_admin),
):
    return {"id": "placeholder", **data}

@router.patch("/{department_id}")
async def update_department(
    department_id: str,
    data: dict,
    current_user: dict = Depends(require_admin),
):
    raise HTTPException(status_code=404, detail="Department not found")

@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: str,
    current_user: dict = Depends(require_admin),
):
    return None