"""
No-operation sandbox adapter (fallback when no sandbox available).
"""

from .base import SandboxAdapter, SandboxCheck


class NoopAdapter(SandboxAdapter):
    """
    Fallback adapter that performs no sandboxing.
    
    Used when:
    - Platform doesn't support sandboxing
    - Required dependencies are missing
    - Sandbox is explicitly disabled
    
    Provides pre-execution path checking as a lightweight alternative.
    """
    
    def __init__(self):
        self._initialized = False
        self._fallback_reason: str = "No sandbox available, using process isolation"
    
    def is_available(self) -> SandboxCheck:
        """Always available as fallback."""
        return SandboxCheck(
            is_available=True,
            errors=[],
            warnings=[self._fallback_reason] if hasattr(self, "_fallback_reason") else []
        )
    
    def get_platform_name(self) -> str:
        return "noop"
    
    async def initialize(self) -> None:
        self._initialized = True
    
    def wrap_command(
        self,
        command: str,
        working_dir: str = None,
        uid: int = None,
        gid: int = None,
    ) -> str:
        """
        Return command unchanged - no sandbox wrapping.
        
        For path checking before execution, use PathRestrictions directly.
        """
        return command
    
    def get_sandbox_profile(self) -> str:
        return "No sandbox (process isolation only)"
