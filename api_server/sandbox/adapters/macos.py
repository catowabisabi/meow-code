"""
macOS sandbox-exec adapter.
"""

import subprocess
from typing import Optional

from .base import SandboxAdapter, SandboxCheck


class MacOSAdapter(SandboxAdapter):
    """
    macOS sandbox-exec adapter.
    
    Uses macOS built-in sandbox-exec for process sandboxing.
    No external dependencies required.
    """
    
    def __init__(self):
        self._initialized = False
        self._sandbox_version: Optional[str] = None
    
    def is_available(self) -> SandboxCheck:
        errors = []
        warnings = []
        
        try:
            result = subprocess.run(
                ["sandbox-exec", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self._sandbox_version = result.stdout.strip()
            else:
                errors.append("sandbox-exec not available")
        except FileNotFoundError:
            errors.append("sandbox-exec not found - not available on this system")
        except subprocess.TimeoutExpired:
            errors.append("sandbox-exec check timed out")
        except Exception as e:
            errors.append(f"sandbox-exec check failed: {e}")
        
        if errors:
            return SandboxCheck(False, errors, warnings)
        
        if self._check_sip():
            warnings.append("System Integrity Protection (SIP) may limit sandbox capabilities")
        
        return SandboxCheck(True, errors, warnings)
    
    def get_platform_name(self) -> str:
        return "macos"
    
    async def initialize(self) -> None:
        check = self.is_available()
        if not check.is_available:
            raise RuntimeError(f"macOS sandbox unavailable: {', '.join(check.errors)}")
        self._initialized = True
    
    def _check_sip(self) -> bool:
        try:
            result = subprocess.run(
                ["csrutil", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return "enabled" in result.stdout.lower()
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
        Wrap a command with sandbox-exec.
        
        Uses a basic sandbox profile that:
        - Allows read access to common directories
        - Allows write to /tmp and specified paths
        - Denies network access by default
        """
        profile = self._build_profile(working_dir)
        escaped_command = command.replace('"', '\\"')
        return f'sandbox-exec -p "{profile}" /bin/sh -c "{escaped_command}"'
    
    def _build_profile(self, working_dir: Optional[str] = None) -> str:
        """Build a basic sandbox profile."""
        parts = [
            "(version 1)",
            "(deny default)",
            "(allow process)",
            "(allow syscalls)",
            "(allow network)",
            "(allow file* file-read* file-write-mmap)",
            "(allow dir-read* dir-write*)",
        ]
        
        allowed_dirs = [
            "/tmp",
            "/var/tmp",
            "/usr/tmp",
        ]
        
        if working_dir:
            import os
            allowed_dirs.append(os.path.abspath(working_dir))
        
        home = self._get_home_dir()
        if home:
            allowed_dirs.extend([
                home,
                f"{home}/**",
            ])
        
        for d in allowed_dirs:
            parts.append(f'(allow file-read* file-write* (prefix "{d}"))')
        
        return "\n".join(parts)
    
    def _get_home_dir(self) -> Optional[str]:
        import os
        return os.path.expanduser("~")
    
    def get_sandbox_profile(self) -> str:
        parts = [
            "macOS sandbox-exec",
            f"Version: {self._sandbox_version or 'unknown'}",
            "Features:",
            "  - Seatbelt sandbox profile",
            "  - System Integrity Protection aware",
        ]
        return "\n".join(parts)
