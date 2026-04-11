"""
WSL2 sandbox adapter.
"""

import shutil
import subprocess
from typing import Optional

from .base import SandboxAdapter, SandboxCheck


class WSL2Adapter(SandboxAdapter):
    """
    WSL2 sandbox adapter.
    
    WSL2 can use bubblewrap but with limited functionality.
    Network isolation may not work properly in WSL2.
    """
    
    def __init__(self):
        self._bwrap_path: Optional[str] = None
        self._initialized = False
    
    def is_available(self) -> SandboxCheck:
        errors = []
        warnings = []
        
        bwrap = shutil.which("bwrap") or shutil.which("bubblewrap")
        if not bwrap:
            errors.append("bubblewrap not found in WSL2 - install via: apt install bubblewrap")
            return SandboxCheck(False, errors, warnings)
        
        self._bwrap_path = bwrap
        
        if not self._check_bwrap_version():
            warnings.append("bubblewrap version may be incompatible with WSL2")
        
        warnings.append("WSL2 sandbox may have reduced functionality compared to native Linux")
        warnings.append("Network isolation may not work in WSL2")
        
        return SandboxCheck(True, errors, warnings)
    
    def get_platform_name(self) -> str:
        return "wsl"
    
    async def initialize(self) -> None:
        check = self.is_available()
        if not check.is_available:
            raise RuntimeError(f"WSL2 sandbox unavailable: {', '.join(check.errors)}")
        self._initialized = True
    
    def _check_bwrap_version(self) -> bool:
        if not self._bwrap_path:
            return False
        try:
            result = subprocess.run(
                [self._bwrap_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def wrap_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
    ) -> str:
        """
        Wrap a command with bubblewrap for WSL2.
        
        WSL2-specific considerations:
        - No network namespace support
        - Limited filesystem isolation
        - May need --cap-add for some operations
        """
        if not self._bwrap_path:
            raise RuntimeError("bubblewrap not initialized")
        
        import os
        
        args = [self._bwrap_path]
        
        if working_dir:
            args.extend(["--chdir", working_dir])
        
        args.extend([
            "--uid", str(uid if uid else os.getuid()),
            "--gid", str(gid if gid else os.getgid()),
            "--hostname", "sandbox-wsl",
        ])
        
        args.append("--")
        args.append(command)
        
        return " ".join(args)
    
    def get_sandbox_profile(self) -> str:
        parts = [
            "WSL2 bubblewrap sandbox",
            f"Bubblewrap path: {self._bwrap_path}",
            "Limitations:",
            "  - No network namespace (WSL2 limitation)",
            "  - May require --cap-add for some operations",
            "  - Filesystem isolation depends on WSL2 config",
        ]
        return "\n".join(parts)
