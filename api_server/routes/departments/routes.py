from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from api_server.middleware.auth import get_current_active_user, require_admin
from api_server.db.repositories.department import DepartmentRepository
from api_server.routes.admin.schemas import DepartmentCreate

router = APIRouter(prefix="/departments", tags=["departments"])


def _get_dept_repo():
    from api_server.db.database import _get_engine
    from api_server.db.session import get_session_factory
    engine = _get_engine()
    session_factory = get_session_factory(engine)
    return session_factory


class DepartmentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None

    class Config:
        from_attributes = True


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None


@router.get("")
async def list_departments(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_active_user),
):
    engine = _get_dept_repo()
    async with engine() as db:
        repo = DepartmentRepository(db)
        departments = await repo.get_all(skip=skip, limit=limit)
        return [DepartmentResponse.model_validate(d) for d in departments]


@router.get("/{department_id}")
async def get_department(
    department_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    engine = _get_dept_repo()
    async with engine() as db:
        repo = DepartmentRepository(db)
        department = await repo.get_by_id(department_id)
        if not department:
            raise HTTPException(status_code=404, detail="Department not found")
        return DepartmentResponse.model_validate(department)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    current_user: dict = Depends(require_admin),
):
    engine = _get_dept_repo()
    async with engine() as db:
        repo = DepartmentRepository(db)
        department = await repo.create(**data.model_dump(exclude_unset=True))
        return DepartmentResponse.model_validate(department)


@router.patch("/{department_id}")
async def update_department(
    department_id: str,
    data: DepartmentUpdate,
    current_user: dict = Depends(require_admin),
):
    engine = _get_dept_repo()
    async with engine() as db:
        repo = DepartmentRepository(db)
        department = await repo.update(department_id, **data.model_dump(exclude_unset=True))
        if not department:
            raise HTTPException(status_code=404, detail="Department not found")
        return DepartmentResponse.model_validate(department)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: str,
    current_user: dict = Depends(require_admin),
):
    engine = _get_dept_repo()
    async with engine() as db:
        repo = DepartmentRepository(db)
        deleted = await repo.delete(department_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Department not found")
        return None
