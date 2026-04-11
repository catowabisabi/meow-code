"""
Platform detection utilities for sandbox system.
"""

import platform
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlatformInfo:
    """Information about the current platform."""
    name: str  # 'linux', 'macos', 'wsl', 'windows', 'unknown'
    is_wsl: bool
    kernel: str
    release: str
    
    def __str__(self) -> str:
        return f"{self.name} (kernel={self.kernel}, is_wsl={self.is_wsl})"


def detect_platform() -> str:
    """
    Detect the current platform with WSL awareness.
    
    Returns:
        'linux', 'macos', 'wsl', 'windows', or 'unknown'
    """
    info = _detect_platform_info()
    return info.name


def get_platform_name() -> str:
    """Alias for detect_platform() for compatibility."""
    return detect_platform()


def _detect_platform_info() -> PlatformInfo:
    """
    Internal platform detection with full info.
    
    WSL detection is based on:
    1. /proc/version contains "Microsoft" on WSL
    2. platform.release() contains "microsoft" on WSL2
    """
    system = platform.system().lower()
    release = platform.release()
    kernel = platform.version()
    
    is_wsl = _is_wsl()
    
    if system == "windows":
        if is_wsl:
            return PlatformInfo(name="wsl", is_wsl=True, kernel=kernel, release=release)
        return PlatformInfo(name="windows", is_wsl=False, kernel=kernel, release=release)
    
    if system == "darwin":
        return PlatformInfo(name="macos", is_wsl=False, kernel=kernel, release=release)
    
    if system == "linux":
        if is_wsl:
            return PlatformInfo(name="wsl", is_wsl=True, kernel=kernel, release=release)
        return PlatformInfo(name="linux", is_wsl=False, kernel=kernel, release=release)
    
    return PlatformInfo(name="unknown", is_wsl=False, kernel=kernel, release=release)


def _is_wsl() -> bool:
    """
    Detect if running under Windows Subsystem for Linux (WSL).
    
    Checks:
    1. /proc/version contains "Microsoft" (WSL1 and WSL2)
    2. platform.release() contains "microsoft" (WSL2)
    """
    # Check platform.release() - works for WSL2
    release = platform.release().lower()
    if "microsoft" in release:
        return True
    
    # Check /proc/version - works for WSL1 and WSL2
    try:
        with open("/proc/version", "r") as f:
            version_content = f.read().lower()
            if "microsoft" in version_content:
                return True
    except (FileNotFoundError, PermissionError):
        pass
    
    # Check for WSL-specific environment variables
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSLENV"):
        return True
    
    return False


def is_linux() -> bool:
    """Check if running on Linux (excluding WSL)."""
    return detect_platform() == "linux"


def is_macos() -> bool:
    """Check if running on macOS."""
    return detect_platform() == "macos"


def is_wsl() -> bool:
    """Check if running on WSL."""
    return detect_platform() == "wsl"


def is_windows() -> bool:
    """Check if running on native Windows (not WSL)."""
    return detect_platform() == "windows"


def is_supported_platform() -> bool:
    """Check if sandbox is supported on this platform."""
    platform = detect_platform()
    return platform in ("linux", "macos", "wsl", "windows")


def get_platform_sandbox_command() -> Optional[str]:
    """
    Get the platform-specific sandbox command available.
    
    Returns:
        'bubblewrap' on Linux, 'sandbox-exec' on macOS,
        'bubblewrap' on WSL, 'processisolation' on Windows,
        or None if no sandbox available.
    """
    import shutil
    
    platform = detect_platform()
    
    if platform in ("linux", "wsl"):
        if shutil.which("bubblewrap"):
            return "bubblewrap"
        return None
    
    if platform == "macos":
        # sandbox-exec is built-in on macOS, no need to check
        return "sandbox-exec"
    
    if platform == "windows":
        # Windows has no native sandbox CLI, but can use process isolation
        return "processisolation"
    
    return None


@dataclass(frozen=True)
class DependencyInfo:
    """Information about a sandbox dependency."""
    name: str
    required: bool
    installed: bool
    install_hint: Optional[str] = None


def get_sandbox_dependencies() -> list[DependencyInfo]:
    """
    Get information about sandbox dependencies for the current platform.
    
    Returns a list of DependencyInfo for each relevant dependency.
    """
    import shutil
    
    platform = detect_platform()
    deps: list[DependencyInfo] = []
    
    if platform in ("linux", "wsl"):
        deps.append(DependencyInfo(
            name="bubblewrap",
            required=True,
            installed=shutil.which("bubblewrap") is not None,
            install_hint="apt install bubblewrap  # Debian/Ubuntu\nyum install bubblewrap  # RHEL/CentOS",
        ))
        deps.append(DependencyInfo(
            name="socat",
            required=False,
            installed=shutil.which("socat") is not None,
            install_hint="apt install socat  # Debian/Ubuntu\nyum install socat  # RHEL/CentOS",
        ))
    
    elif platform == "macos":
        # sandbox-exec is built-in, no dependency check needed
        pass
    
    elif platform == "windows":
        # No external dependencies needed
        pass
    
    return deps
