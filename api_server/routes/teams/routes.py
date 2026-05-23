from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from api_server.middleware.auth import get_current_active_user, require_admin
from api_server.db.repositories.team import TeamRepository
from api_server.routes.admin.schemas import TeamCreate

router = APIRouter(prefix="/teams", tags=["teams"])


def _get_team_repo():
    from api_server.db.database import _get_engine
    from api_server.db.session import get_session_factory
    engine = _get_engine()
    session_factory = get_session_factory(engine)
    return session_factory


class TeamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    department_id: Optional[str] = None
    leader_id: Optional[str] = None

    class Config:
        from_attributes = True


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[str] = None
    leader_id: Optional[str] = None


@router.get("")
async def list_teams(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_active_user),
):
    engine = _get_team_repo()
    async with engine() as db:
        repo = TeamRepository(db)
        teams = await repo.get_all(skip=skip, limit=limit)
        return [TeamResponse.model_validate(t) for t in teams]


@router.get("/{team_id}")
async def get_team(
    team_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    engine = _get_team_repo()
    async with engine() as db:
        repo = TeamRepository(db)
        team = await repo.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return TeamResponse.model_validate(team)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_team(
    data: TeamCreate,
    current_user: dict = Depends(require_admin),
):
    engine = _get_team_repo()
    async with engine() as db:
        repo = TeamRepository(db)
        team = await repo.create(**data.model_dump(exclude_unset=True))
        return TeamResponse.model_validate(team)


@router.patch("/{team_id}")
async def update_team(
    team_id: str,
    data: TeamUpdate,
    current_user: dict = Depends(require_admin),
):
    engine = _get_team_repo()
    async with engine() as db:
        repo = TeamRepository(db)
        team = await repo.update(team_id, **data.model_dump(exclude_unset=True))
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return TeamResponse.model_validate(team)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    current_user: dict = Depends(require_admin),
):
    engine = _get_team_repo()
    async with engine() as db:
        repo = TeamRepository(db)
        deleted = await repo.delete(team_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Team not found")
        return None
