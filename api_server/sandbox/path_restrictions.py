"""
Path restriction checking for filesystem access control.
"""

import fnmatch
import os
from pathlib import Path


class PathRestrictions:
    """
    Filesystem path restriction checker.
    
    Implements allow/deny semantics for path access control.
    Deny patterns take precedence over allow patterns.
    """
    
    def __init__(
        self,
        allow_read: list[str] = None,
        deny_read: list[str] = None,
        allow_write: list[str] = None,
        deny_write: list[str] = None,
    ):
        self.allow_read = [self._normalize(p) for p in (allow_read or [])]
        self.deny_read = [self._normalize(p) for p in (deny_read or [])]
        self.allow_write = [self._normalize(p) for p in (allow_write or [])]
        self.deny_write = [self._normalize(p) for p in (deny_write or [])]
    
    @staticmethod
    def _normalize(path: str) -> Path:
        """Normalize a path to absolute form."""
        return Path(os.path.expanduser(path)).resolve()
    
    def can_read(self, path: str) -> bool:
        """Check if a path can be read."""
        p = self._normalize(path)
        
        # Explicit deny always blocks
        if self._matches_any(p, self.deny_read):
            return False
        
        # If allow list exists, path must match it
        if self.allow_read:
            return self._matches_any(p, self.allow_read)
        
        return True
    
    def can_write(self, path: str) -> bool:
        """Check if a path can be written."""
        p = self._normalize(path)
        
        if self._matches_any(p, self.deny_write):
            return False
        
        if self.allow_write:
            return self._matches_any(p, self.allow_write)
        
        return True
    
    def can_execute(self, path: str) -> bool:
        """Check if a path can be executed (same as read for files)."""
        return self.can_read(path)
    
    def _matches_any(self, path: Path, patterns: list[Path]) -> bool:
        """Check if path matches any of the patterns."""
        for pattern in patterns:
            if self._matches(path, pattern):
                return True
        return False
    
    def _matches(self, path: Path, pattern: Path) -> bool:
        """Check if path is covered by pattern."""
        # Exact match
        if path == pattern:
            return True
        
        # Path is under pattern directory
        try:
            pattern_str = str(pattern)
            path_str = str(path)
            
            # Direct parent check
            if path.parent == pattern:
                return True
            
            # Prefix check (path starts with pattern/)
            if path_str.startswith(pattern_str + os.sep):
                return True
            
            # Or pattern is a parent of path
            if pattern in path.parents:
                return True
                
        except ValueError:
            # On Windows, Path comparison can fail for mixed separators
            pass
        
        return False
    
    def check_access(self, path: str, mode: str = "r") -> tuple[bool, str]:
        """
        Check if access is allowed, returning (allowed, reason).
        
        Args:
            path: Path to check
            mode: Access mode ('r', 'w', 'x')
        
        Returns:
            (True, "") if allowed
            (False, reason) if denied
        """
        if mode == "r":
            if not self.can_read(path):
                return False, f"Read access denied: {path}"
        elif mode == "w":
            if not self.can_write(path):
                return False, f"Write access denied: {path}"
        elif mode == "x":
            if not self.can_execute(path):
                return False, f"Execute access denied: {path}"
        
        return True, ""
    
    def check_command_access(self, command: str) -> tuple[bool, str]:
        """
        Check if a shell command can access certain paths.
        
        This is a heuristic check that parses the command for path arguments.
        Returns (allowed, blocked_paths).
        """
        import shlex
        
        blocked = []
        try:
            parts = shlex.split(command)
        except ValueError:
            return True, ""
        
        for part in parts:
            # Skip flags and options
            if part.startswith("-"):
                continue
            
            # Expand ~ and env vars
            expanded = os.path.expanduser(os.path.expandvars(part))
            
            # Check if it looks like a path
            if os.path.isabs(expanded) and os.path.exists(expanded):
                if not self.can_read(expanded):
                    blocked.append(expanded)
                elif not self.can_write(expanded):
                    blocked.append(expanded)
        
        if blocked:
            return False, f"Command accesses blocked paths: {', '.join(blocked)}"
        
        return True, ""


def check_path_safety(path: str) -> tuple[bool, str]:
    """
    Basic path safety check.
    
    Returns (is_safe, reason) where is_safe is True if the path
    doesn't point to sensitive system locations.
    """
    import os
    
    path = os.path.abspath(os.path.expanduser(path))
    
    dangerous = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "/root/.ssh",
        "/home/*/.ssh",
        "/.ssh",
        "/proc/1/environ",
    ]
    
    for d in dangerous:
        if fnmatch.fnmatch(path, d) or path.startswith(d + "/"):
            return False, f"Path is in protected location: {d}"
    
    return True, ""
