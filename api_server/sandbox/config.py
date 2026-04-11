"""
Sandbox configuration dataclasses.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FilesystemRestrictions:
    """
    Filesystem access restrictions for sandbox.
    
    Paths can be specified as absolute paths or glob patterns.
    Matching is done with prefix comparison (e.g., /home/user/src
    matches /home/user/src, /home/user/src/subdir, etc.).
    """
    # Directories/files that can be read (empty list = allow all except deny)
    allow_read: list[str] = field(default_factory=list)
    # Directories/files that cannot be read (takes precedence over allow)
    deny_read: list[str] = field(default_factory=list)
    # Directories/files that can be written (empty list = allow all except deny)
    allow_write: list[str] = field(default_factory=list)
    # Directories/files that cannot be written (takes precedence over allow)
    deny_write: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate configuration."""
        # Ensure no path appears in both allow and deny
        for path in self.allow_read:
            if path in self.deny_read:
                raise ValueError(f"Path '{path}' cannot be in both allow_read and deny_read")
        for path in self.allow_write:
            if path in self.deny_write:
                raise ValueError(f"Path '{path}' cannot be in both allow_write and deny_write")


@dataclass
class NetworkRestrictions:
    """
    Network access restrictions for sandbox.
    
    Domain matching supports glob patterns (e.g., *.example.com).
    Denied domains take precedence over allowed domains.
    """
    # Allowed domains (empty list = allow all except deny)
    allowed_domains: list[str] = field(default_factory=list)
    # Denied domains (takes precedence over allow)
    denied_domains: list[str] = field(default_factory=list)
    # Allow Unix domain sockets
    allow_unix_sockets: bool = False
    # Allow binding to localhost only
    allow_local_binding: bool = False


@dataclass
class SandboxConfig:
    """
    Complete sandbox configuration for shell command execution.
    """
    # Filesystem restrictions
    filesystem: FilesystemRestrictions = field(default_factory=FilesystemRestrictions)
    # Network restrictions
    network: NetworkRestrictions = field(default_factory=NetworkRestrictions)
    # Default timeout in seconds
    timeout_seconds: float = 120.0
    # Commands to exclude from sandboxing (e.g., ['ls', 'cat', 'echo'])
    excluded_commands: list[str] = field(default_factory=list)
    # Fail execution if sandbox cannot be enabled
    fail_if_unavailable: bool = False
    # Fail on any sandbox violation
    fail_on_violation: bool = True
    # Enable network restrictions (requires socat on Linux)
    enable_network_restrictions: bool = True
    # Bubblewrap data directory (default: ~/.local/share/bubblewrap)
    bwrap_data_dir: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive, got {self.timeout_seconds}")
        if self.timeout_seconds > 3600:
            raise ValueError("timeout_seconds cannot exceed 3600 (1 hour)")
    
    @classmethod
    def default(cls) -> "SandboxConfig":
        """
        Create a default sandbox configuration.
        
        Default allows read/write to user's home directory,
        with no network restrictions.
        """
        import os
        home = os.path.expanduser("~")
        return cls(
            filesystem=FilesystemRestrictions(
                allow_read=[home],
                allow_write=[home],
            ),
            network=NetworkRestrictions(),
            timeout_seconds=120.0,
        )
    
    @classmethod
    def strict(cls) -> "SandboxConfig":
        """
        Create a strict sandbox configuration.
        
        No filesystem or network access by default.
        """
        return cls(
            filesystem=FilesystemRestrictions(
                allow_read=[],
                deny_read=["/"],
                allow_write=[],
                deny_write=["/"],
            ),
            network=NetworkRestrictions(
                denied_domains=["*"],
            ),
            timeout_seconds=60.0,
        )
    
    def with_filesystem_allowed(self, *paths: str) -> "SandboxConfig":
        """Create a new config with additional allowed filesystem paths."""
        new_fs = FilesystemRestrictions(
            allow_read=self.filesystem.allow_read + list(paths),
            deny_read=self.filesystem.deny_read.copy(),
            allow_write=self.filesystem.allow_write + list(paths),
            deny_write=self.filesystem.deny_write.copy(),
        )
        return SandboxConfig(
            filesystem=new_fs,
            network=self.network,
            timeout_seconds=self.timeout_seconds,
            excluded_commands=self.excluded_commands.copy(),
            fail_if_unavailable=self.fail_if_unavailable,
            fail_on_violation=self.fail_on_violation,
            enable_network_restrictions=self.enable_network_restrictions,
            bwrap_data_dir=self.bwrap_data_dir,
        )


@dataclass
class SandboxResult:
    """Result of a sandbox operation."""
    # Whether sandbox was applied
    sandbox_enabled: bool
    # Platform adapter used
    adapter_name: str
    # Any warnings or info messages
    messages: list[str] = field(default_factory=list)
    # Errors that occurred
    errors: list[str] = field(default_factory=list)
    # Whether violations were detected
    violation_detected: bool = False
    # Violation details if any
    violations: list[str] = field(default_factory=list)
    
    @property
    def is_healthy(self) -> bool:
        """Check if sandbox is functioning properly."""
        return len(self.errors) == 0 and not self.violation_detected
