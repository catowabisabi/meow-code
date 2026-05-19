from fastapi import APIRouter, Depends, HTTPException, status
from api_server.middleware.auth import get_current_active_user, require_admin
from api_server.db.repositories.user import UserRepository
from api_server.db.repositories.role import RoleRepository
from api_server.db.repositories.team import TeamRepository
from api_server.db.repositories.department import DepartmentRepository
from api_server.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users")
async def list_users(
    page: int = 1,
    limit: int = 10,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    users = await user_repo.get_all()
    start = (page - 1) * limit
    end = start + limit
    return {"items": users[start:end], "total": len(users)}

@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    data: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    user = await user_repo.update(user_id, **data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    await user_repo.delete(user_id)
    return None

@router.get("/roles")
async def list_roles(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    role_repo = RoleRepository(db)
    return await role_repo.get_all()

@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(
    data: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    role_repo = RoleRepository(db)
    return await role_repo.create(**data)

@router.patch("/roles/{role_id}")
async def update_role(
    role_id: str,
    data: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    role_repo = RoleRepository(db)
    role = await role_repo.update(role_id, **data)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    role_repo = RoleRepository(db)
    await role_repo.delete(role_id)
    return None

@router.get("/departments")
async def list_departments(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    dept_repo = DepartmentRepository(db)
    return await dept_repo.get_all()

@router.post("/departments", status_code=status.HTTP_201_CREATED)
async def create_department(
    data: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    dept_repo = DepartmentRepository(db)
    return await dept_repo.create(**data)

@router.get("/teams")
async def list_teams(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    team_repo = TeamRepository(db)
    return await team_repo.get_all()

@router.post("/teams", status_code=status.HTTP_201_CREATED)
async def create_team(
    data: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    team_repo = TeamRepository(db)
    return await team_repo.create(**data)