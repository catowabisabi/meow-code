"""
Sandbox-specific exceptions.
"""


class SandboxException(Exception):
    """Base exception for sandbox-related errors."""
    pass


class SandboxViolation(SandboxException):
    """
    Raised when a sandbox restriction is violated.
    
    Attributes:
        restriction_type: Type of restriction ('filesystem' or 'network')
        path: The path or resource that was blocked
        message: Human-readable description of the violation
    """
    def __init__(
        self,
        message: str,
        restriction_type: str = "filesystem",
        path: str = ""
    ):
        super().__init__(message)
        self.restriction_type = restriction_type
        self.path = path


class SandboxUnavailable(SandboxException):
    """
    Raised when sandbox cannot be initialized but is required.
    
    This can occur when:
    - Required dependencies (bubblewrap, etc.) are not installed
    - Platform does not support sandboxing
    - Kernel does not support required features
    """
    def __init__(self, message: str, platform: str = "", errors: list[str] = None):
        super().__init__(message)
        self.platform = platform
        self.errors = errors or []


class SandboxConfigurationError(SandboxException):
    """Raised when sandbox configuration is invalid."""
    pass


class SandboxCommandBlocked(SandboxException):
    """
    Raised when a command is explicitly blocked by sandbox policy.
    
    This differs from SandboxViolation in that it represents
    an explicit policy decision rather than accidental access.
    """
    def __init__(self, command: str, reason: str = ""):
        message = f"Command blocked by sandbox policy: {command}"
        if reason:
            message += f" (reason: {reason})"
        super().__init__(message)
        self.command = command
        self.reason = reason
