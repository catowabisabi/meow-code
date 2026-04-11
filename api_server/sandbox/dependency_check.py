"""
Dependency checking for sandbox system.
"""

import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from .platform import detect_platform


@dataclass
class DependencyCheck:
    """Result of dependency checking."""
    # Whether all required dependencies are available
    is_available: bool
    # Platform this check was performed on
    platform: str
    # List of errors (missing required dependencies)
    errors: list[str] = field(default_factory=list)
    # List of warnings (missing optional dependencies)
    warnings: list[str] = field(default_factory=list)
    # Detailed dependency information
    dependencies: dict[str, bool] = field(default_factory=dict)
    
    def __str__(self) -> str:
        parts = [f"Platform: {self.platform}"]
        if self.errors:
            parts.append(f"Errors: {', '.join(self.errors)}")
        if self.warnings:
            parts.append(f"Warnings: {', '.join(self.warnings)}")
        parts.append(f"Available: {self.is_available}")
        return " | ".join(parts)


def check_dependencies() -> DependencyCheck:
    """
    Check if sandbox dependencies are available on the current platform.
    
    This performs a comprehensive check of all required and optional
    dependencies for sandbox functionality.
    
    Returns:
        DependencyCheck with detailed status information
    """
    platform = detect_platform()
    errors = []
    warnings = []
    deps = {}
    
    if platform == "linux":
        _check_linux_dependencies(errors, warnings, deps)
    elif platform == "wsl":
        _check_wsl_dependencies(errors, warnings, deps)
    elif platform == "macos":
        _check_macos_dependencies(errors, warnings, deps)
    elif platform == "windows":
        _check_windows_dependencies(errors, warnings, deps)
    else:
        errors.append(f"Unknown platform: {platform}")
    
    return DependencyCheck(
        is_available=len(errors) == 0,
        platform=platform,
        errors=errors,
        warnings=warnings,
        dependencies=deps,
    )


def _check_linux_dependencies(errors: list, warnings: list, deps: dict):
    """Check dependencies for Linux platforms."""
    # Check for bubblewrap (required)
    bwrap_path = shutil.which("bwrap") or shutil.which("bubblewrap")
    deps["bubblewrap"] = bwrap_path is not None
    if not bwrap_path:
        errors.append(
            "bubblewrap not found - install via: apt install bubblewrap"
        )
    
    # Check for unshare (needed for some sandbox features)
    deps["unshare"] = shutil.which("unshare") is not None
    if not deps["unshare"]:
        warnings.append(
            "unshare not found - some sandbox features may be limited"
        )
    
    # Check for socat (optional, for network restrictions)
    deps["socat"] = shutil.which("socat") is not None
    if not deps["socat"]:
        warnings.append(
            "socat not found - network restrictions will be limited"
        )
    
    # Check kernel support
    if not _check_kernel_support():
        errors.append(
            "Kernel does not support user namespaces (CONFIG_USER_NS=y required)"
        )


def _check_wsl_dependencies(errors: list, warnings: list, deps: dict):
    """Check dependencies for WSL platforms."""
    # WSL has limited bubblewrap support
    bwrap_path = shutil.which("bwrap") or shutil.which("bubblewrap")
    deps["bubblewrap"] = bwrap_path is not None
    
    if not bwrap_path:
        errors.append(
            "bubblewrap not found in WSL2 - install via: apt install bubblewrap"
        )
        errors.append(
            "WSL2 requires bubblewrap for sandbox functionality"
        )
    else:
        # Check bubblewrap version (need 0.3.0+)
        try:
            result = subprocess.run(
                ["bwrap", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version_str = result.stdout.strip()
            # Basic version check - could be more sophisticated
            if version_str:
                deps["bubblewrap_version"] = version_str
        except Exception:
            warnings.append("Could not determine bubblewrap version")
    
    # SOCAT for network restrictions
    deps["socat"] = shutil.which("socat") is not None
    if not deps["socat"]:
        warnings.append(
            "socat not found - network restrictions will be limited in WSL2"
        )
    
    # WSL-specific warnings
    warnings.append(
        "WSL2 sandbox may have reduced functionality compared to native Linux"
    )


def _check_macos_dependencies(errors: list, warnings: list, deps: dict):
    """Check dependencies for macOS platforms."""
    # sandbox-exec is built-in on macOS (since macOS 10.5)
    deps["sandbox_exec"] = True  # Built-in, always available
    
    # Check if sandbox is enabled at all (may be disabled in some configurations)
    try:
        result = subprocess.run(
            ["sandbox-exec", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        deps["sandbox_version"] = result.stdout.strip()
    except FileNotFoundError:
        errors.append(
            "sandbox-exec not found - sandbox functionality unavailable"
        )
    except subprocess.TimeoutExpired:
        warnings.append("sandbox-exec check timed out")
    
    # macOS-specific considerations
    if _is_macos_sip_enabled():
        warnings.append(
            "System Integrity Protection (SIP) may limit sandbox capabilities"
        )


def _check_windows_dependencies(errors: list, warnings: list, deps: dict):
    """Check dependencies for Windows platforms."""
    # Windows has no native sandbox CLI
    deps["windows_sandbox"] = False
    
    # Windows uses process isolation as alternative
    warnings.append(
        "Windows does not support bubblewrap/sandbox-exec - using process isolation fallback"
    )
    warnings.append(
        "Process isolation provides limited security (user separation only)"
    )


def _check_kernel_support() -> bool:
    """Check if the kernel supports user namespaces."""
    try:
        # Try to read the kernel config (if available)
        import os
        if os.path.exists("/proc/config.gz"):
            # Check for CONFIG_USER_NS
            import gzip
            with gzip.open("/proc/config.gz", "rt") as f:
                for line in f:
                    if line.strip() == "CONFIG_USER_NS=y":
                        return True
        elif os.path.exists("/boot/config-" + platform.uname().release):
            with open("/boot/config-" + platform.uname().release, "r") as f:
                for line in f:
                    if line.strip() == "CONFIG_USER_NS=y":
                        return True
        
        # Try unshare to check runtime support
        result = subprocess.run(
            ["unshare", "--user", "--map-root-user", "echo", "ok"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        pass
    
    return False


def _is_macos_sip_enabled() -> bool:
    """Check if System Integrity Protection is enabled on macOS."""
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


def get_installation_instructions() -> dict[str, str]:
    """
    Get platform-specific installation instructions for sandbox dependencies.
    
    Returns a dict mapping platform names to installation instructions.
    """
    return {
        "linux": """
On Debian/Ubuntu:
    sudo apt update
    sudo apt install bubblewrap socat

On Fedora/RHEL/CentOS:
    sudo dnf install bubblewrap socat

On Arch Linux:
    sudo pacman -S bubblewrap socat
""",
        "wsl": """
WSL2 requires Linux tools installed within the WSL distribution:
    
    sudo apt update
    sudo apt install bubblewrap socat

Note: WSL2 has limited support for some sandbox features.
For full sandbox functionality, consider using a native Linux system.
""",
        "macos": """
sandbox-exec is built-in on macOS and no additional installation is needed.

Note: Some sandbox features may be limited by System Integrity Protection (SIP).
""",
        "windows": """
Windows does not support bubblewrap or sandbox-exec.

For secure command execution on Windows:
- Consider using Windows Sandbox or Windows Defender Application Guard
- The API server will use process isolation as a fallback
""",
    }
