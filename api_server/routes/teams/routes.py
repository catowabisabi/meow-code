from fastapi import APIRouter, Depends, HTTPException, status
from api_server.middleware.auth import get_current_active_user, require_admin

router = APIRouter(prefix="/teams", tags=["teams"])

@router.get("")
async def list_teams(
    current_user: dict = Depends(get_current_active_user),
):
    return []

@router.get("/{team_id}")
async def get_team(
    team_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    raise HTTPException(status_code=404, detail="Team not found")

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_team(
    data: dict,
    current_user: dict = Depends(require_admin),
):
    return {"id": "placeholder", **data}

@router.patch("/{team_id}")
async def update_team(
    team_id: str,
    data: dict,
    current_user: dict = Depends(require_admin),
):
    raise HTTPException(status_code=404, detail="Team not found")

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    current_user: dict = Depends(require_admin),
):
    return None