"""
Sandbox system for secure shell command execution.

Provides filesystem and network restrictions for shell commands,
with platform-specific adapters (Linux/bubblewrap, macOS/sandbox-exec, etc.).
"""

from .config import SandboxConfig, FilesystemRestrictions, NetworkRestrictions
from .platform import detect_platform, get_platform_name
from .dependency_check import check_dependencies, DependencyCheck
from .path_restrictions import PathRestrictions
from .exceptions import SandboxViolation, SandboxUnavailable
from .sandboxed_shell import SandboxedShellExecutor

__all__ = [
    # Config
    "SandboxConfig",
    "FilesystemRestrictions",
    "NetworkRestrictions",
    # Platform
    "detect_platform",
    "get_platform_name",
    # Dependencies
    "check_dependencies",
    "DependencyCheck",
    # Path restrictions
    "PathRestrictions",
    # Exceptions
    "SandboxViolation",
    "SandboxUnavailable",
    # Main executor
    "SandboxedShellExecutor",
]


def get_sandbox_adapter():
    """
    Get the appropriate sandbox adapter for the current platform.
    
    Returns the best available adapter (bubblewrap on Linux,
    sandbox-exec on macOS, or NoopAdapter as fallback).
    """
    from .platform import detect_platform
    from .adapters import (
        BubblewrapAdapter,
        MacOSAdapter,
        WSL2Adapter,
        WindowsAdapter,
        NoopAdapter,
    )
    
    platform = detect_platform()
    
    adapters = {
        "linux": BubblewrapAdapter,
        "macos": MacOSAdapter,
        "wsl": WSL2Adapter,
        "windows": WindowsAdapter,
    }
    
    adapter_class = adapters.get(platform, NoopAdapter)
    adapter = adapter_class()
    
    # Check if adapter is available, fall back to NoopAdapter if not
    is_available, errors = adapter.is_available()
    if not is_available:
        # Return NoopAdapter with warning about why the preferred adapter failed
        noop = NoopAdapter()
        noop._fallback_reason = f"Preferred adapter ({adapter_class.__name__}) unavailable: {', '.join(errors)}"
        return noop
    
    return adapter
