"""
Container Service - Docker/Podman 容器管理。
替代原本 SSH 到 claude.ai 遠程容器的設計，改為完全本地容器。
"""
import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Callable

logger = logging.getLogger(__name__)


class ContainerStatus(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ContainerRuntime(str, Enum):
    DOCKER = "docker"
    PODMAN = "podman"


SUPPORTED_IMAGES = {
    "python:3.12-slim": "Python 3.12",
    "python:3.11-slim": "Python 3.11",
    "node:20-alpine": "Node.js 20 (Alpine)",
    "node:18-alpine": "Node.js 18 (Alpine)",
    "ubuntu:24.04": "Ubuntu 24.04",
    "ubuntu:22.04": "Ubuntu 22.04",
}


@dataclass
class ContainerSession:
    id: str
    runtime: ContainerRuntime
    image: str
    container_id: str
    status: ContainerStatus
    created_at: str
    work_dir: str
    ttl_seconds: int = 1800
    last_activity: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ExecutionResult:
    session_id: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    artifacts: List[dict] = field(default_factory=list)


class ContainerService:
    def __init__(self):
        self._sessions: dict[str, ContainerSession] = {}
        self._runtime: Optional[ContainerRuntime] = None
        self._check_runtime()

    def _check_runtime(self):
        import shutil
        if shutil.which("docker"):
            self._runtime = ContainerRuntime.DOCKER
        elif shutil.which("podman"):
            self._runtime = ContainerRuntime.PODMAN
        else:
            self._runtime = None
            logger.warning("No container runtime (Docker/Podman) found")

    @property
    def is_available(self) -> bool:
        return self._runtime is not None

    def get_runtime(self) -> Optional[ContainerRuntime]:
        return self._runtime

    async def create_session(
        self,
        image: str = "python:3.12-slim",
        work_dir: str = "/workspace",
        ttl_seconds: int = 1800,
        env: Optional[dict] = None,
    ) -> ContainerSession:
        if not self.is_available:
            raise RuntimeError("Container runtime not available")

        session_id = f"ocr_{uuid.uuid4().hex[:12]}"
        container_id = await self._create_container(image, work_dir, env)

        session = ContainerSession(
            id=session_id,
            runtime=self._runtime,
            image=image,
            container_id=container_id,
            status=ContainerStatus.RUNNING,
            created_at=datetime.utcnow().isoformat(),
            work_dir=work_dir,
            ttl_seconds=ttl_seconds,
            last_activity=datetime.utcnow().isoformat(),
        )
        self._sessions[session_id] = session
        return session

    async def _create_container(
        self,
        image: str,
        work_dir: str,
        env: Optional[dict],
    ) -> str:
        cmd = [self._runtime.value, "run", "-d"]
        cmd.extend(["--rm"])
        cmd.extend(["-w", work_dir])
        cmd.extend(["--privileged", image, "sleep", "infinity"])

        if env:
            for k, v in env.items():
                cmd.extend(["-e", f"{k}={v}"])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Failed to create container: {stderr.decode()}")

        container_id = stdout.decode().strip()[:12]
        return container_id

    async def execute(
        self,
        session_id: str,
        command: str,
        timeout_seconds: int = 300,
    ) -> ExecutionResult:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if session.status != ContainerStatus.RUNNING:
            raise RuntimeError(f"Session {session_id} is not running")

        start_time = datetime.utcnow()

        cmd = [
            self._runtime.value, "exec",
            session.container_id,
            "sh", "-c", command,
        ]

        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=timeout_seconds,
            )
            stdout, stderr = await proc.communicate()
            exit_code = proc.returncode
        except asyncio.TimeoutError:
            exit_code = -1
            stdout = b"Command timed out"
            stderr = b""

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        session.last_activity = datetime.utcnow().isoformat()

        return ExecutionResult(
            session_id=session_id,
            exit_code=exit_code,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            duration_ms=duration_ms,
        )

    async def execute_streaming(
        self,
        session_id: str,
        command: str,
        on_output: Callable[[str], None],
        timeout_seconds: int = 300,
    ) -> ExecutionResult:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        cmd = [
            self._runtime.value, "exec",
            "-i", session.container_id,
            "sh", "-c", command,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        try:
            stdout, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )
            output = stdout.decode("utf-8", errors="replace")
            if on_output and output:
                on_output(output)
            exit_code = proc.returncode
        except asyncio.TimeoutError:
            proc.kill()
            output = "Command timed out"
            exit_code = -1

        duration_ms = 0
        session.last_activity = datetime.utcnow().isoformat()

        return ExecutionResult(
            session_id=session_id,
            exit_code=exit_code,
            stdout=output,
            stderr="",
            duration_ms=duration_ms,
        )

    async def upload_file(
        self,
        session_id: str,
        path: str,
        content: bytes,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        import base64
        encoded = base64.b64encode(content).decode()

        cmd = [
            self._runtime.value, "exec", "-i",
            session.container_id,
            "sh", "-c",
            f"echo '{encoded}' | base64 -d > {path}",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        session.last_activity = datetime.utcnow().isoformat()
        return proc.returncode == 0

    async def download_file(
        self,
        session_id: str,
        path: str,
    ) -> Optional[bytes]:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        cmd = [
            self._runtime.value, "exec",
            session.container_id,
            "base64", path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return None

        import base64
        try:
            return base64.b64decode(stdout)
        except Exception:
            return None

    async def destroy_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.status = ContainerStatus.STOPPING

        cmd = [self._runtime.value, "stop", session.container_id]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception:
            pass

        self._sessions.pop(session_id, None)
        return True

    def get_session(self, session_id: str) -> Optional[ContainerSession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[ContainerSession]:
        return list(self._sessions.values())

    def extend_ttl(self, session_id: str, additional_seconds: int) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.ttl_seconds += additional_seconds
        return True


_container_service: Optional[ContainerService] = None


def get_container_service() -> ContainerService:
    global _container_service
    if _container_service is None:
        _container_service = ContainerService()
    return _container_service
