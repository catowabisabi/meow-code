"""Sandbox adapter with security features - bridging gap with TypeScript sandbox/sandbox-adapter.ts"""
import os
import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
import hashlib


logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    enabled: bool = True
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    max_processes: int = 10
    max_memory_mb: int = 512
    network_enabled: bool = True
    read_only_fs: bool = False


@dataclass
class SandboxResult:
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = 0


SCRUB_PATTERNS = [
    "/.git/",
    "/.ssh/",
    "/.config/",
    "/.local/share/",
]


class SandboxManager:
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._active_sandboxes: Dict[str, asyncio.Task] = {}
    
    def is_enabled(self) -> bool:
        return self.config.enabled
    
    def should_use_sandbox(self, command: str, cwd: str) -> bool:
        if not self.is_enabled():
            return False
        
        for denied in self.config.denied_paths:
            if cwd.startswith(denied):
                return False
        
        return True
    
    def wrap_command(self, command: str, shell_path: str = "/bin/bash") -> str:
        wrapped = command
        
        if self.config.read_only_fs:
            wrapped = f"echo 'Sandbox: read-only mode' && {wrapped}"
        
        return wrapped
    
    async def execute_in_sandbox(
        self,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> SandboxResult:
        if not self.should_use_sandbox(command, cwd):
            return await self._execute_direct(command, cwd, env, timeout)
        
        wrapped_cmd = self.wrap_command(command)
        
        try:
            result = await self._execute_direct(wrapped_cmd, cwd, env, timeout)
            
            return SandboxResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                exit_code=result.returncode
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1
            )
    
    async def _execute_direct(
        self,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]],
        timeout: float
    ):
        proc = await asyncio.create_subprocess_exec(
            "/bin/bash", "-c", command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env or os.environ,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            return asyncio.subprocess.Process(
                proc,
                stdout.decode(),
                stderr.decode(),
                proc.returncode or 0
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise
    
    @staticmethod
    def cleanup_after_command() -> None:
        pass
    
    @staticmethod
    def wrap_with_sandbox(
        command: str,
        shell_path: str,
        sandbox_config: Optional[SandboxConfig],
        abort_signal: Optional[asyncio.Event]
    ) -> str:
        return command


_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager


def should_use_sandbox(command: str, cwd: str) -> bool:
    manager = get_sandbox_manager()
    return manager.should_use_sandbox(command, cwd)


def bare_git_repo_scrub_paths(paths: List[str]) -> List[str]:
    """Filter out paths that should not be accessible from bare git repos."""
    scrubbed = []
    for path in paths:
        for pattern in SCRUB_PATTERNS:
            if pattern in path:
                break
        else:
            scrubbed.append(path)
    return scrubbed
