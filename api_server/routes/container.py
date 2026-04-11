"""
FastAPI routes for Container API.
提供 Docker/Podman 容器管理功能。
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..services.container import (
    get_container_service,
    ContainerSession,
    ExecutionResult,
    ContainerRuntime,
    SUPPORTED_IMAGES,
)


router = APIRouter(prefix="/container", tags=["container"])


class ContainerCreateRequest(BaseModel):
    image: str = "python:3.12-slim"
    work_dir: str = "/workspace"
    ttl_seconds: int = 1800
    env: Optional[dict] = None


class ContainerExecuteRequest(BaseModel):
    command: str
    timeout_seconds: int = 300


class ContainerUploadRequest(BaseModel):
    path: str
    content: str


class ContainerResponse(BaseModel):
    session_id: str
    runtime: str
    image: str
    status: str
    work_dir: str
    ttl_seconds: int


class ExecutionResponse(BaseModel):
    session_id: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    artifacts: list[dict]


@router.get("/status")
async def container_status():
    service = get_container_service()
    return {
        "available": service.is_available,
        "runtime": service.get_runtime().value if service.get_runtime() else None,
        "supported_images": SUPPORTED_IMAGES,
    }


@router.post("/sessions", response_model=ContainerResponse)
async def create_container(data: ContainerCreateRequest):
    service = get_container_service()

    if not service.is_available:
        raise HTTPException(
            status_code=503,
            detail="Container runtime not available. Please install Docker or Podman.",
        )

    if data.image not in SUPPORTED_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image. Supported: {list(SUPPORTED_IMAGES.keys())}",
        )

    try:
        session = await service.create_session(
            image=data.image,
            work_dir=data.work_dir,
            ttl_seconds=data.ttl_seconds,
            env=data.env,
        )
        return ContainerResponse(
            session_id=session.id,
            runtime=session.runtime.value,
            image=session.image,
            status=session.status.value,
            work_dir=session.work_dir,
            ttl_seconds=session.ttl_seconds,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_containers():
    service = get_container_service()
    sessions = service.list_sessions()
    return {
        "sessions": [
            ContainerResponse(
                session_id=s.id,
                runtime=s.runtime.value,
                image=s.image,
                status=s.status.value,
                work_dir=s.work_dir,
                ttl_seconds=s.ttl_seconds,
            )
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}", response_model=ContainerResponse)
async def get_container(session_id: str):
    service = get_container_service()
    session = service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return ContainerResponse(
        session_id=session.id,
        runtime=session.runtime.value,
        image=session.image,
        status=session.status.value,
        work_dir=session.work_dir,
        ttl_seconds=session.ttl_seconds,
    )


@router.post("/sessions/{session_id}/execute", response_model=ExecutionResponse)
async def execute_in_container(session_id: str, data: ContainerExecuteRequest):
    service = get_container_service()
    session = service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = await service.execute(
            session_id=session_id,
            command=data.command,
            timeout_seconds=data.timeout_seconds,
        )
        return ExecutionResponse(
            session_id=result.session_id,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=result.duration_ms,
            artifacts=result.artifacts,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/upload")
async def upload_to_container(session_id: str, data: ContainerUploadRequest):
    service = get_container_service()
    session = service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    import base64
    try:
        content = base64.b64decode(data.content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 content")

    success = await service.upload_file(session_id, data.path, content)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload file")

    return {"ok": True, "path": data.path}


@router.get("/sessions/{session_id}/download")
async def download_from_container(session_id: str, path: str):
    service = get_container_service()
    session = service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    content = await service.download_file(session_id, path)

    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    import base64
    return {
        "path": path,
        "content": base64.b64encode(content).decode(),
    }


@router.delete("/sessions/{session_id}")
async def destroy_container(session_id: str):
    service = get_container_service()
    success = await service.destroy_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"ok": True}


@router.post("/sessions/{session_id}/extend")
async def extend_container_ttl(session_id: str, seconds: int = Query(default=1800, ge=60, le=7200)):
    service = get_container_service()
    success = service.extend_ttl(session_id, seconds)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"ok": True, "ttl_seconds": seconds}
