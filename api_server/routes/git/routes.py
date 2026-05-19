from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from api_server.services.git import GitService
from api_server.middleware.auth import get_current_active_user

router = APIRouter(prefix="/git", tags=["git"])


class StageRequest(BaseModel):
    files: List[str]


class CommitRequest(BaseModel):
    message: str


class CheckoutRequest(BaseModel):
    branch: str


class CreateBranchRequest(BaseModel):
    name: str
    from_branch: Optional[str] = None


class DiffRequest(BaseModel):
    file_path: Optional[str] = None
    staged: bool = False


def get_git_service() -> GitService:
    return GitService(repo_path="/workspace")


@router.get("/status")
async def get_status(
    current_user: dict = Depends(get_current_active_user),
):
    git_service = get_git_service()
    status = git_service.get_status()
    return {
        "branch": status.branch,
        "staged": status.staged,
        "modified": status.modified,
        "untracked": status.untracked,
        "conflicted": status.conflicted,
    }


@router.post("/stage")
async def stage_files(
    request: StageRequest,
    current_user: dict = Depends(get_current_active_user),
):
    git_service = get_git_service()
    git_service.stage(request.files)
    return {"success": True}


@router.post("/unstage")
async def unstage_files(
    request: StageRequest,
    current_user: dict = Depends(get_current_active_user),
):
    git_service = get_git_service()
    git_service.unstage(request.files)
    return {"success": True}


@router.post("/commit")
async def commit(
    request: CommitRequest,
    current_user: dict = Depends(get_current_active_user),
):
    git_service = get_git_service()
    try:
        commit_hash = git_service.commit(request.message)
        return {"hash": commit_hash}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/log")
async def get_log(
    max_count: int = Query(default=50, le=100),
    current_user: dict = Depends(get_current_active_user),
):
    git_service = get_git_service()
    commits = git_service.get_log(max_count)
    return {"commits": [
        {
            "hash": c.hash,
            "message": c.message,
            "author": c.author,
            "date": c.date,
        }
        for c in commits
    ]}


@router.get("/diff")
async def get_diff(
    file_path: Optional[str] = None,
    staged: bool = False,
    current_user: dict = Depends(get_current_active_user),
):
    git_service = get_git_service()
    diffs = git_service.get_diff(file_path, staged)
    return {"diffs": [
        {
            "file": d.file,
            "status": d.status,
            "additions": d.additions,
            "deletions": d.deletions,
            "hunks": d.hunks,
        }
        for d in diffs
    ]}


@router.get("/branches")
async def get_branches(
    current_user: dict = Depends(get_current_active_user),
):
    git_service = get_git_service()
    return git_service.get_branches()


@router.post("/checkout")
async def checkout(
    request: CheckoutRequest,
    current_user: dict = Depends(get_current_active_user),
):
    git_service = get_git_service()
    git_service.checkout(request.branch)
    return {"success": True}


@router.post("/branch")
async def create_branch(
    request: CreateBranchRequest,
    current_user: dict = Depends(get_current_active_user),
):
    git_service = get_git_service()
    git_service.create_branch(request.name, request.from_branch)
    return {"success": True}