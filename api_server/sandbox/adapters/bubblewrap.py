"""
Bubblewrap sandbox adapter for Linux.
"""

import os
import shutil
import subprocess
from typing import Optional

from .base import SandboxAdapter, SandboxCheck


class BubblewrapAdapter(SandboxAdapter):
    """
    Bubblewrap sandbox adapter for Linux.
    
    Bubblewrap creates lightweight namespace isolation for processes.
    Requires bubblewrap and optionally socat for network restrictions.
    """
    
    def __init__(self):
        self._bwrap_path: Optional[str] = None
        self._initialized = False
    
    def is_available(self) -> SandboxCheck:
        errors = []
        warnings = []
        
        bwrap = shutil.which("bwrap") or shutil.which("bubblewrap")
        if not bwrap:
            errors.append("bubblewrap not found - install via: apt install bubblewrap")
            return SandboxCheck(False, errors, warnings)
        
        self._bwrap_path = bwrap
        
        if not self._check_version():
            warnings.append("bubblewrap version may be old, upgrade recommended")
        
        if not self._check_kernel_support():
            errors.append("Kernel does not support user namespaces")
            return SandboxCheck(False, errors, warnings)
        
        if not shutil.which("socat"):
            warnings.append("socat not found - network restrictions will be limited")
        
        return SandboxCheck(True, errors, warnings)
    
    def get_platform_name(self) -> str:
        return "linux"
    
    async def initialize(self) -> None:
        check = self.is_available()
        if not check.is_available:
            raise RuntimeError(f"Bubblewrap unavailable: {', '.join(check.errors)}")
        self._initialized = True
    
    def _check_version(self) -> bool:
        if not self._bwrap_path:
            return False
        try:
            result = subprocess.run(
                [self._bwrap_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = result.stdout.strip()
            if output:
                parts = output.split()
                if len(parts) >= 2:
                    try:
                        version = parts[1].split(".")
                        major = int(version[0])
                        minor = int(version[1]) if len(version) > 1 else 0
                        return major > 0 or (major == 0 and minor >= 3)
                    except (ValueError, IndexError):
                        pass
        except Exception:
            pass
        return True
    
    def _check_kernel_support(self) -> bool:
        try:
            result = subprocess.run(
                ["unshare", "--user", "--map-root-user", "echo", "ok"],
                capture_output=True,
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
        Wrap a command with bubblewrap.
        
        Example output:
            bwrap --ro-bind /home /home --dev /dev --proc /proc echo hello
        """
        if not self._bwrap_path:
            raise RuntimeError("Bubblewrap not initialized")
        
        args = [self._bwrap_path]
        
        if working_dir:
            args.extend(["--chdir", working_dir])
        
        if uid is not None:
            args.extend(["--uid", str(uid)])
        else:
            args.extend(["--uid", str(os.getuid())])
        
        if gid is not None:
            args.extend(["--gid", str(gid)])
        else:
            args.extend(["--gid", str(os.getgid())])
        
        args.extend([
            "--hostname", "sandbox",
            "--share-net",
            "--unshare-pid",
            "--unshare-uts",
            "--unshare-ipc",
        ])
        
        args.append("--")
        args.append(command)
        
        return " ".join(args)
    
    def build_bwrap_args(
        self,
        filesystem_restrictions,
        network_restrictions=None,
    ) -> list[str]:
        """
        Build bubblewrap mount arguments from restriction config.
        
        Args:
            filesystem_restrictions: FilesystemRestrictions instance
            network_restrictions: NetworkRestrictions instance (optional)
        
        Returns:
            List of bubblewrap arguments
        """
        args = []
        
        deny_read_paths = set()
        deny_write_paths = set()
        allow_read_paths = set()
        allow_write_paths = set()
        
        if filesystem_restrictions:
            deny_read_paths.update(filesystem_restrictions.deny_read)
            deny_write_paths.update(filesystem_restrictions.deny_write)
            allow_read_paths.update(filesystem_restrictions.allow_read)
            allow_write_paths.update(filesystem_restrictions.allow_write)
        
        for path in deny_read_paths:
            if os.path.isdir(path):
                args.extend(["--lock-file", path])
        
        if deny_read_paths or deny_write_paths:
            args.append("--ro-bind-try")
            args.extend(["/etc", "/etc"])
        
        for path in allow_read_paths:
            if os.path.isdir(path):
                args.extend(["--ro-bind", path, path])
            elif os.path.isfile(path):
                args.extend(["--ro-bind", path, path])
        
        for path in allow_write_paths:
            if os.path.isdir(path):
                args.extend(["--bind", path, path])
            elif os.path.isfile(path):
                args.extend(["--bind", path, path])
        
        args.extend([
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
        ])
        
        if not network_restrictions or not network_restrictions.allow_unix_sockets:
            args.extend(["--unshare-net"])
        
        return args
    
    def get_sandbox_profile(self) -> str:
        parts = [
            f"Bubblewrap sandbox (path: {self._bwrap_path})",
            "Features:",
            "  - User namespace isolation",
            "  - Network namespace isolation",
            "  - Mount namespace for filesystem",
            "  - PID namespace isolation",
        ]
        return "\n".join(parts)
