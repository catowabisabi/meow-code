from fastapi import APIRouter, Depends, HTTPException, status
from api_server.middleware.auth import get_current_active_user, require_admin
from api_server.db.repositories.department import DepartmentRepository
from api_server.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/departments", tags=["departments"])

@router.get("")
async def list_departments(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = DepartmentRepository(db)
    return await repo.get_all()

@router.get("/{department_id}")
async def get_department(
    department_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = DepartmentRepository(db)
    department = await repo.get_by_id(department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return department

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_department(
    data: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = DepartmentRepository(db)
    return await repo.create(**data)

@router.patch("/{department_id}")
async def update_department(
    department_id: str,
    data: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = DepartmentRepository(db)
    department = await repo.update(department_id, **data)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return department

@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = DepartmentRepository(db)
    await repo.delete(department_id)
    return None