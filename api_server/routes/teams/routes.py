from fastapi import APIRouter, Depends, HTTPException, status
from api_server.middleware.auth import get_current_active_user, require_admin
from api_server.db.repositories.team import TeamRepository
from api_server.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/teams", tags=["teams"])

@router.get("")
async def list_teams(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TeamRepository(db)
    return await repo.get_all()

@router.get("/{team_id}")
async def get_team(
    team_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TeamRepository(db)
    team = await repo.get_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_team(
    data: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = TeamRepository(db)
    return await repo.create(**data)

@router.patch("/{team_id}")
async def update_team(
    team_id: str,
    data: dict,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = TeamRepository(db)
    team = await repo.update(team_id, **data)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = TeamRepository(db)
    await repo.delete(team_id)
    return None