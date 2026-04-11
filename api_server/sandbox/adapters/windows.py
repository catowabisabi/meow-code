"""
Windows process isolation adapter.
"""

from typing import Optional

from .base import SandboxAdapter, SandboxCheck


class WindowsAdapter(SandboxAdapter):
    """
    Windows process isolation adapter.
    
    Windows doesn't have bubblewrap or sandbox-exec.
    Uses Windows process isolation features as fallback.
    """
    
    def __init__(self):
        self._initialized = False
    
    def is_available(self) -> SandboxCheck:
        return SandboxCheck(
            is_available=True,
            errors=[],
            warnings=[
                "Windows sandbox provides limited isolation",
                "Using Windows process boundaries as security layer",
                "No namespace or mount restrictions available",
            ]
        )
    
    def get_platform_name(self) -> str:
        return "windows"
    
    async def initialize(self) -> None:
        self._initialized = True
    
    def wrap_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
    ) -> str:
        """
        Wrap command for Windows.
        
        On Windows, we use process boundaries but cannot
        apply namespace restrictions. The command is returned
        as-is with potential working directory via cd.
        """
        if working_dir:
            return f'cd /d "{working_dir}" && {command}'
        return command
    
    def get_sandbox_profile(self) -> str:
        return "Windows process isolation (limited)\n  - No namespace isolation\n  - No filesystem restrictions\n  - Using Windows ACLs only"
